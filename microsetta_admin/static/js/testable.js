highFive = function(){ return 5; }
ret7 = function(){return 12;}

// Expose any unit testable functionality to node's module.exports
// This will enable these functions to be called by our test suite.
// If statement prevents dereferencing null when script is included in browser.
if (typeof module !== 'undefined' && typeof module.exports !== 'undefined'){
  module.exports = {
    "highFive": highFive,
    "ret7": ret7
  }
}
