# OpenML Server API Software Documentation

This is the Python-based OpenML REST API server.
It's a rewrite of our [old backend](http://github.com/openml/openml) built with a
modern Python-based stack.

### What's changed?
For an overview about how the REST API is changing, visit the
[migration guide](migration.md).


### Why a new REST API?
The current production REST API has been with us for over a decade, and is still trotting along.
However, it's built on a number of technologies which fell out of favor and some of its design decisions do not match current-day expectations.
The current REST API would need significant refactoring to bring it up-to-date.

Instead, we chose to reimplement the REST API in Python, since most of our core developers are more familiar with it than PHP, it has good packages and tooling for modern software development, and it's more familiar to the ML community.
We hope that a Python-based REST API will be easier to understand, maintain, and extend by future contributors.



!!! question "Looking to access data on OpenML?"

    If you simply want to access data stored on OpenML in a programmatic way,
    please have a look at connector packages in
    [Python](https://openml.github.io/openml-python/main/),
    [Java](https://github.com/openml/openml-java),
    or [R](http://openml.github.io/openml-r/).

    If you are looking to interface directly with the REST API, and are looking
    for documentation on the REST API endpoints, visit the
    [APIs](https://openml.org/apis) page.
