package statedb

import (
	"math/big"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/vm"

	sdk "github.com/cosmos/cosmos-sdk/types"
)

// ExtStateDB defines an extension to the interface provided by the go-ethereum
// codebase to support additional state transition functionalities. In particular
// it supports appending a new entry to the state journal through
// AppendJournalEntry so that the state can be reverted after running
// stateful precompiled contracts.
type ExtStateDB interface {
	vm.StateDB
	AppendJournalEntry(JournalEntry)
}

// Keeper provide underlying storage of StateDB
type Keeper interface {
	Transfer(ctx sdk.Context, sender, recipient common.Address, amount *big.Int) error
	AddBalance(ctx sdk.Context, addr common.Address, amount *big.Int) error
	SubBalance(ctx sdk.Context, addr common.Address, amount *big.Int) error
	SetBalance(ctx sdk.Context, addr common.Address, amount *big.Int) error
	GetBalance(ctx sdk.Context, addr common.Address) *big.Int

	// Read methods
	GetAccount(ctx sdk.Context, addr common.Address) *Account
	GetState(ctx sdk.Context, addr common.Address, key common.Hash) common.Hash
	GetCode(ctx sdk.Context, codeHash common.Hash) []byte
	// the callback returns false to break early
	ForEachStorage(ctx sdk.Context, addr common.Address, cb func(key, value common.Hash) bool)

	// Write methods, only called by `StateDB.Commit()`
	SetAccount(ctx sdk.Context, addr common.Address, account Account) error
	DeleteState(ctx sdk.Context, addr common.Address, key common.Hash)
	SetState(ctx sdk.Context, addr common.Address, key common.Hash, value []byte)
	DeleteCode(ctx sdk.Context, codeHash []byte)
	SetCode(ctx sdk.Context, codeHash []byte, code []byte)
	DeleteAccount(ctx sdk.Context, addr common.Address) error
}
