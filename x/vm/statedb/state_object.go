package statedb

import (
	"bytes"
	"sort"

	"github.com/ethereum/go-ethereum/common"

	"github.com/cosmos/evm/x/vm/types"

	storetypes "cosmossdk.io/store/types"

	sdk "github.com/cosmos/cosmos-sdk/types"
)

// Account is the Ethereum consensus representation of accounts.
// These objects are stored in the storage of auth module.
type Account struct {
	Nonce    uint64
	CodeHash []byte
}

// NewEmptyAccount returns an empty account.
func NewEmptyAccount() *Account {
	return &Account{
		CodeHash: types.EmptyCodeHash,
	}
}

// IsContract returns if the account contains contract code.
func (acct Account) IsContract() bool {
	return !types.IsEmptyCodeHash(acct.CodeHash)
}

// Storage represents in-memory cache/buffer of contract storage.
type Storage map[common.Hash]common.Hash

// SortedKeys sort the keys for deterministic iteration
func (s Storage) SortedKeys() []common.Hash {
	keys := make([]common.Hash, 0, len(s))
	for k := range s {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool {
		return bytes.Compare(keys[i].Bytes(), keys[j].Bytes()) < 0
	})
	return keys
}

// stateObject is the state of an account
type stateObject struct {
	db *StateDB

	// to check the dirtiness of the account ,it's nil if the account is newly created
	originalAccount *Account

	account Account
	code    []byte

	// state storage
	originStorage Storage
	dirtyStorage  Storage

	address common.Address

	// flags
	dirtyCode bool
	suicided  bool
}

// newObject creates a state object.
func newObject(db *StateDB, address common.Address, origAccount *Account) *stateObject {
	var account Account
	if origAccount == nil {
		account = *(NewEmptyAccount())
	} else {
		account = *origAccount
	}

	return &stateObject{
		db:              db,
		address:         address,
		originalAccount: origAccount,
		account:         account,
		originStorage:   make(Storage),
		dirtyStorage:    make(Storage),
	}
}

// empty returns whether the account is considered empty.
func (s *stateObject) empty() bool {
	return s.account.Nonce == 0 && types.IsEmptyCodeHash(s.account.CodeHash)
}

func (s *stateObject) markSuicided() {
	s.suicided = true
}

// AddPrecompileFn appends to the journal an entry
// with a snapshot of the multi-store and events
// previous to the precompile call
func (s *stateObject) AddPrecompileFn(cms storetypes.CacheMultiStore, events sdk.Events) {
	s.db.journal.append(precompileCallChange{
		multiStore: cms,
		events:     events,
	})
}

//
// Attribute accessors
//

// Returns the address of the contract/account
func (s *stateObject) Address() common.Address {
	return s.address
}

// Code returns the contract code associated with this object, if any.
func (s *stateObject) Code() []byte {
	if s.code != nil {
		return s.code
	}

	if types.IsEmptyCodeHash(s.CodeHash()) {
		return nil
	}

	code := s.db.keeper.GetCode(s.db.ctx, common.BytesToHash(s.CodeHash()))
	s.code = code

	return code
}

// CodeSize returns the size of the contract code associated with this object,
// or zero if none.
func (s *stateObject) CodeSize() int {
	return len(s.Code())
}

// SetCode set contract code to account
func (s *stateObject) SetCode(codeHash common.Hash, code []byte) {
	prevcode := s.Code()
	s.db.journal.append(codeChange{
		account:  &s.address,
		prevhash: s.CodeHash(),
		prevcode: prevcode,
	})
	s.setCode(codeHash, code)
}

func (s *stateObject) setCode(codeHash common.Hash, code []byte) {
	s.code = code
	s.account.CodeHash = codeHash[:]
	s.dirtyCode = true
}

// SetCode set nonce to account
func (s *stateObject) SetNonce(nonce uint64) {
	s.db.journal.append(nonceChange{
		account: &s.address,
		prev:    s.account.Nonce,
	})
	s.setNonce(nonce)
}

func (s *stateObject) setNonce(nonce uint64) {
	s.account.Nonce = nonce
}

// CodeHash returns the code hash of account
func (s *stateObject) CodeHash() []byte {
	return s.account.CodeHash
}

// Nonce returns the nonce of account
func (s *stateObject) Nonce() uint64 {
	return s.account.Nonce
}

// GetCommittedState query the committed state
func (s *stateObject) GetCommittedState(key common.Hash) common.Hash {
	if value, cached := s.originStorage[key]; cached {
		return value
	}
	// If no live objects are available, load it from keeper
	value := s.db.keeper.GetState(s.db.ctx, s.Address(), key)
	s.originStorage[key] = value
	return value
}

// GetState query the current state (including dirty state)
func (s *stateObject) GetState(key common.Hash) common.Hash {
	if value, dirty := s.dirtyStorage[key]; dirty {
		return value
	}
	return s.GetCommittedState(key)
}

// SetState sets the contract state
func (s *stateObject) SetState(key common.Hash, value common.Hash) {
	// If the new value is the same as old, don't set
	prev := s.GetState(key)
	if prev == value {
		return
	}
	// New value is different, update and journal the change
	s.db.journal.append(storageChange{
		account:  &s.address,
		key:      key,
		prevalue: prev,
	})
	s.setState(key, value)
}

func (s *stateObject) setState(key, value common.Hash) {
	s.dirtyStorage[key] = value
}
