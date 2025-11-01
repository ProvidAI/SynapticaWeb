// Stub module for pino-pretty
// This is an optional dev dependency for pretty-printing logs
// Not needed in production builds
module.exports = function pinoPretty() {
  return function prettifier() {
    return ''
  }
}

