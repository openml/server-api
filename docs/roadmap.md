The REST API is currently under development.
It's does not yet have feature parity with the PHP-based REST API.
We are currently working on Phase 1 and Phase 2 in parallel, and to deploy to production before the end of 2026.
The sunset date of the PHP-based REST API will depend on the progress of this reimplementation and that of some other required server services.

## Phase 1: Achieve Feature Parity

The first goal is _rough_ feature parity.
This means that we want to expose the same endpoints with the same general responses.
We may deviate in case the original implementation had an oversight or a bug, and fix those along the way.
We can be pragmatic about this, for example, copying over a complex query from the PHP API.
This phase is considered complete when the output of the new REST API can be mapped to output of the old REST API for all endpoints the PHP-based API has and the [migration guide](migration.md) is done.


## Phase 2: Modernizing the API

We are also working on incorporating modern standards like [RFC9457](https://www.rfc-editor.org/rfc/rfc9457.html) for error reporting, better use of JSON types, including authentication in the request's HTTP header instead of the URL, or changing HTTP methods or paths to better reflect the behavior of the endpoint.

## Phase 3: Revisiting the Data(base)

After the PHP-based API has sunset, the Python-based API will be the only one connecting to the database.
This means we can start cleaning the database data and schema more freely, such as standardizing value formats where possible (e.g., (un)quoting contributor names in the dataset's contributor field), use more appropriate data types, drop deprecated tables or columns, and more.

We can also start supporting different file formats for e.g., task splits or prediction files.

## Phase 4: New Features

Richer metadata for assets on OpenML (e.g., structured citation data), collaboration features, OAuth support, and support for other data modalities are just some of the features we want to work on in 2027 and beyond.


## Other Services
Besides the REST API, there are a few other components which need to be developed:

 - A logstash pipeline to populate ES indices based on the database data and/or a message queue. Currently, the PHP-based REST API directly puts documents into ES indices, which makes it prone to getting out of sync, and requires an ES server to run to use/test the API in ways which otherwise would not require an ES index.
 - Evaluation Engine. A service which computes meta-features for datasets, including the "qualities" and "features" you find with datasets.
