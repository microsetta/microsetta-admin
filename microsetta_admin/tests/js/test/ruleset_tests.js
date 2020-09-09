const ruleset = require("../../../static/js/ruleset");

QUnit.module('Ruleset', function() {
  QUnit.test('Test Variables', function(assert){
    var x = new ruleset.NamedExpression("x", 7);
    var y = new ruleset.NamedExpression("y", 12);
    assert.equal(x.value, 7, "Get Value");
    assert.equal(y.value, 12, "Get Value");
    x.value = 15;
    assert.equal(x.value, 15, "Set Value");
  });

  QUnit.test('Test Boolean Expressions', function(assert){
    var a = new ruleset.NamedExpression("x", true);
    var b = new ruleset.NamedExpression("y", false);

    var and = new ruleset.AndExpression(a,b);
    var or = new ruleset.OrExpression(a,b);
    var eq = new ruleset.EqualsExpression(a,b);
    var notA = new ruleset.NotExpression(a);

    for (var i = 0; i <= 1; i++)
      for (var j = 0; j <= 1; j++)
      {
        a.value = i;
        b.value = j;

        assert.equal(and.value, i && j);
        assert.equal(or.value, i || j);
        assert.equal(eq.value, i == j);
        assert.equal(notA.value, !i);
      }
  });

  QUnit.test('Test Delegates', function(assert) {
    var x = new ruleset.NamedExpression("x", 1);
    var y = new ruleset.NamedExpression("y", 1);
    var z = new ruleset.NamedExpression("z", 2);

    var xs = [];
    var ys = [];
    var zs = [];
    var addToList = function(valX, valY){
      xs.push(valX);
      ys.push(valY);
    };

    var addToList2 = function(valZ){
      zs.push(valZ)
    };

    var delegate = new ruleset.DelegateOutput(addToList, x, y);
    var delegate2 = new ruleset.DelegateOutput(addToList2, z);

    for (var i = 0; i < 5; i++)
    {
      x.value = x.value + y.value;
      z.value = x.value + y.value;
      y.value = x.value + y.value;
      z.value = x.value + y.value;
    }

    // Fibonacci is 1,1,2,3,5,8,13,21,34,55,89,144,233
    assert.deepEqual(xs, [1,2,2,5,5,13,13,34,34,89,89]);
    assert.deepEqual(ys, [1,1,3,3,8,8,21,21,55,55,144]);
    assert.deepEqual(zs, [2,3,5,8,13,21,34,55,89,144,233])
  });

  QUnit.test('Test OnChange Actually Changes', function(assert) {
    var x = new ruleset.NamedExpression("x", 1);

    var xs = [];
    var addToList = function(valX){
      xs.push(valX);
    };
    new ruleset.DelegateOutput(addToList, x);

    x.value = 2;
    x.value = 3;
    x.value = 3;
    x.value = 2;
    x.value = 2;
    x.value = 1;
    x.value = 1;

    assert.deepEqual(xs, [1,2,3,2,1])
  })
});
