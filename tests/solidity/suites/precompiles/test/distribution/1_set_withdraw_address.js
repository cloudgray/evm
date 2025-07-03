const {expect} = require('chai');
const hre = require('hardhat');

describe('Distribution – set withdraw address', function () {
    const DIST_ADDRESS = '0x0000000000000000000000000000000000000801';
    const gasLimit = 1_000_000;

    let distribution, signer;

    before(async () => {
        [signer] = await hre.ethers.getSigners();
        distribution = await hre.ethers.getContractAt('DistributionI', DIST_ADDRESS);
    });

    it('should set withdraw address and emit SetWithdrawerAddress event', async function () {
        const signerBech32 = 'cosmos1cml96vmptgw99syqrrz8az79xer2pcgp95srxm'
        const newWithdrawAddress = 'cosmos1fx944mzagwdhx0wz7k9tfztc8g3lkfk6pzezqh';
        const tx = await distribution
            .connect(signer)
            .setWithdrawAddress(signer.address, newWithdrawAddress, {gasLimit});
        const receipt = await tx.wait(2);
        console.log('SetWithdrawAddress tx hash:', receipt.hash);

        const evt = receipt.logs
            .map(log => {
                try {
                    return distribution.interface.parseLog(log);
                } catch {
                    return null;
                }
            })
            .find(e => e && e.name === 'SetWithdrawerAddress');
        expect(evt, 'SetWithdrawerAddress event must be emitted').to.exist;
        expect(evt.args.caller).to.equal(signer.address);
        expect(evt.args.withdrawerAddress).to.equal(newWithdrawAddress);

        const withdrawer = await distribution.delegatorWithdrawAddress(signer.address);
        console.log('Withdraw address:', withdrawer);
        expect(withdrawer).to.equal(newWithdrawAddress);
    });
});