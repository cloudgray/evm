const { expect } = require('chai')
const hre = require('hardhat')

describe('StakingI – createValidator with Bech32 operator address', function () {
  const STAKING_ADDRESS = '0x0000000000000000000000000000000000000800'
  const BECH32_ADDRESS  = '0x0000000000000000000000000000000000000400'

  let staking, bech32, signer

  /**
   * Convert the raw tuple from staking.validator(...)
   * into an object that mirrors the Validator struct.
   */
  function parseValidator(raw) {
    return {
      operatorAddress:   raw[0],
      consensusPubkey:   raw[1],
      jailed:            raw[2],
      status:            raw[3],
      tokens:            raw[4],
      delegatorShares:   raw[5],
      description:       raw[6],
      unbondingHeight:   raw[7],
      unbondingTime:     raw[8],
      commission:        raw[9],
      minSelfDelegation: raw[10],
    }
  }

  before(async () => {
    [signer] = await hre.ethers.getSigners()

    // Instantiate the StakingI precompile contract
    staking = await hre.ethers.getContractAt('StakingI', STAKING_ADDRESS)
    // Instantiate the Bech32I precompile contract for address conversion
    bech32  = await hre.ethers.getContractAt('Bech32I',  BECH32_ADDRESS)
  })

  it('should create a validator successfully using a Bech32-encoded operator address', async function () {
    // Define the validator’s descriptive metadata
    const description = {
      moniker:         'TestValidator',
      identity:        'id123',
      website:         'https://example.com',
      securityContact: 'sec@example.com',
      details:         'unit-test validator',
    }

    // Set initial commission parameters (18-decimal precision)
    const commissionRates = {
      rate:           hre.ethers.parseUnits('0.05', 18), // 5%
      maxRate:        hre.ethers.parseUnits('0.20', 18), // 20%
      maxChangeRate:  hre.ethers.parseUnits('0.01', 18), // 1%
    }

    // Configure the remaining createValidator arguments
    const minSelfDelegation = 1
    const pubkey            = 'nfJ0axJC9dhta1MAE1EBFaVdxxkYzxYrBaHuJVjG//M='
    const deposit           = hre.ethers.parseEther('1') // self-delegate 1 native token

    // Submit the createValidator transaction
    const tx = await staking.connect(signer).createValidator(
        description,
        commissionRates,
        minSelfDelegation,
        signer.address,
        pubkey,
        deposit
    )

    // Wait for 2 confirmations and log the transaction hash
    const receipt = await tx.wait(2)
    console.log('Transaction hash:', receipt.hash)

    // Find and parse the CreateValidator event from the transaction logs
    const parsed = receipt.logs
        .map(log => {
          try {
            return staking.interface.parseLog(log)
          } catch {
            return null
          }
        })
        .find(evt => evt && evt.name === 'CreateValidator')

    expect(parsed, 'CreateValidator event must be emitted').to.exist
    expect(parsed.args.validatorAddress).to.equal(signer.address)
    expect(parsed.args.value).to.equal(deposit)

    // Retrieve and log the on-chain Validator struct
    const rawInfo = await staking.validator(signer.address)
    console.log('Validator info:', rawInfo)

    // Parse the raw tuple into a structured object
    const info = parseValidator(rawInfo)

    // Verify that each field matches the expected values
    expect(info.operatorAddress.toLowerCase()).to.equal(signer.address.toLowerCase())
    expect(info.consensusPubkey).to.equal(pubkey)
    expect(info.jailed).to.be.false
    expect(info.status).to.equal(3n)                      // BondStatus.Bonded === 3
    expect(info.tokens).to.equal(deposit)
    expect(info.delegatorShares).to.be.gt(0n)
    expect(info.description).to.equal(description.details)
    expect(info.unbondingHeight).to.equal(0n)
    expect(info.unbondingTime).to.equal(0n)
    expect(info.commission).to.equal(commissionRates.rate)
    expect(info.minSelfDelegation).to.equal(BigInt(minSelfDelegation))
  })
})