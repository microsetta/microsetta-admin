const testable = require("../../../static/js/testable");

QUnit.module('testable', function() {
  QUnit.test('Test testable functions', function(assert){
    assert.equal(testable.highFive(), 5, "Get high 5");
    assert.equal(testable.ret7(), 7, "Returns 7");
    })
});
