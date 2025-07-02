const {expect} = require('chai')
const hre = require('hardhat')

/**
 * Convert the raw tuple from staking.redelegation(...)
 * into an object that mirrors the RedelegationOutput struct.
 */
function formatRedelegation(res) {
    const delegatorAddress = res[0]
    const validatorSrcAddress = res[1]
    const validatorDstAddress = res[2]
    const rawEntries = res[3] // array of RedelegationEntry

    const entries = rawEntries.map(entry => {
        const [
            creationHeight,
            completionTime,
            initialBalance,
            sharesDst,
        ] = entry

        return {
            creationHeight: Number(creationHeight),
            completionTime: Number(completionTime),
            initialBalance: BigInt(initialBalance.toString()),
            sharesDst: BigInt(sharesDst.toString()),
        }
    })

    return {
        delegatorAddress,
        validatorSrcAddress,
        validatorDstAddress,
        entries,
    }
}

describe('Staking – redelegate with event and state assertions', function () {
    const STAKING_ADDRESS = '0x0000000000000000000000000000000000000800'
    const gasLimit = 1_000_000 // skip gas estimation for simplicity

    let staking, bech32, signer

    before(async () => {
        [signer] = await hre.ethers.getSigners()
        // instantiate StakingI and Bech32I precompile contracts
        staking = await hre.ethers.getContractAt('StakingI', STAKING_ADDRESS)
    })

    it('should redelegate tokens and emit Redelegate event', async function () {
        const srcValBech32 = 'cosmosvaloper10jmp6sgh4cc6zt3e8gw05wavvejgr5pw4xyrql'
        const dstValBech32 = 'cosmosvaloper1cml96vmptgw99syqrrz8az79xer2pcgpqqyk2g'

        // decode bech32 → hex for event comparisons
        const srcValHex = '0x7cB61D4117AE31a12E393a1Cfa3BaC666481D02E'
        const dstValHex = '0xC6Fe5D33615a1C52c08018c47E8Bc53646A0E101'

        // 1) query current delegation to source validator
        const beforeDelegation = await staking.delegation(signer.address, srcValBech32)
        const amount = beforeDelegation.balance.amount
        console.log('Current delegation to srcVal:', amount.toString())

        // 2) query redelegation entries before
        const beforeRaw = await staking.redelegation(signer.address, srcValBech32, dstValBech32)
        const beforeR = formatRedelegation(beforeRaw)
        const entriesBefore = beforeR.entries.length

        // 3) send the redelegate transaction
        const tx = await staking
            .connect(signer)
            .redelegate(signer.address, srcValBech32, dstValBech32, amount, {gasLimit: gasLimit})
        const receipt = await tx.wait(2)
        console.log('Redelegate tx hash:', tx.hash, 'gas used:', receipt.gasUsed.toString())

        // 4) parse and assert the Redelegate event
        const redelegateEvt = receipt.logs
            .map(log => {
                try {
                    return staking.interface.parseLog(log)
                } catch {
                    return null
                }
            })
            .find(evt => evt && evt.name === 'Redelegate')
        expect(redelegateEvt, 'Redelegate event should be emitted').to.exist
        expect(redelegateEvt.args.delegatorAddress).to.equal(signer.address)
        expect(redelegateEvt.args.validatorSrcAddress).to.equal(srcValHex)
        expect(redelegateEvt.args.validatorDstAddress).to.equal(dstValHex)
        expect(redelegateEvt.args.amount).to.equal(amount)
        const completionTime = BigInt(redelegateEvt.args.completionTime.toString())
        expect(completionTime > 0n, 'completionTime should be positive').to.be.true

        // 5) query redelegation state after
        const afterRaw = await staking.redelegation(signer.address, srcValBech32, dstValBech32)
        const afterR = formatRedelegation(afterRaw)
        const entriesAfter = afterR.entries.length

        // Assert that a new redelegation entry was created
        expect(entriesAfter).to.equal(
            entriesBefore + 1,
            'Number of redelegation entries should increase by 1'
        )
        // Assert that the latest entry initialBalance matches the redelegated amount
        expect(afterR.entries[0].initialBalance).to.equal(
            BigInt(amount.toString()),
            'Redelegation entry initialBalance should match redelegated amount'
        )
    })
})
