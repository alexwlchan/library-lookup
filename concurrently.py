"""
From https://github.com/alexwlchan/concurrently
"""

import concurrent.futures
import itertools


def concurrently(fn, inputs, *, max_concurrency=5):
    """
    Calls the function ``fn`` on the values ``inputs``.

    ``fn`` should be a function that takes a single input, which is the
    individual values in the iterable ``inputs``.

    Generates (input, output) tuples as the calls to ``fn`` complete.

    """
    # Make sure we get a consistent iterator throughout, rather than
    # getting the first element repeatedly.
    fn_inputs = iter(inputs)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(fn, input): input
            for input in itertools.islice(fn_inputs, max_concurrency)
        }

        while futures:
            done, _ = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )

            for fut in done:
                original_input = futures.pop(fut)
                yield original_input, fut.result()

            for input in itertools.islice(fn_inputs, len(done)):
                fut = executor.submit(fn, input)
                futures[fut] = input
