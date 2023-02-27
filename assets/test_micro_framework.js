// see https://alexwlchan.net/2023/testing-javascript-without-a-framework/

function it(description, body_of_test) {
  const result = document.createElement('p');
  result.classList.add('test_result')

  try {
    body_of_test();
    result.classList.add('success');
    result.innerHTML = description;
  } catch (error) {
    result.classList.add('failure');
    result.innerHTML = `${description}<br/><pre>${error}</pre>`;
  }

  document.body.appendChild(result);
}

function assertEqual(x, y) {
  if (
    x === y || (
      typeof x === 'object' &&
      typeof y === 'object' &&
      x.length === y.length &&
      x.every((element, index) => element === y[index])
    )
  ) {
    return;
  } else {
    console.log(x);
    console.log(y);
    throw new Error(`${x} != ${y}`);
  }
}

function assertTrue(x) {
  assertEqual(x, true);
}

function assertFalse(x) {
  assertEqual(x, false);
}
