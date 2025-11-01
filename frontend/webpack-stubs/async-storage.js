// Stub module for @react-native-async-storage/async-storage
// This is not needed in browser environments where localStorage is available
const stub = {
  getItem: () => Promise.resolve(null),
  setItem: () => Promise.resolve(),
  removeItem: () => Promise.resolve(),
  clear: () => Promise.resolve(),
  getAllKeys: () => Promise.resolve([]),
  multiGet: () => Promise.resolve([]),
  multiSet: () => Promise.resolve(),
  multiRemove: () => Promise.resolve(),
}

// Support both CommonJS and ES module imports
module.exports = stub
module.exports.default = stub

