# openml_expdb Database

The `openml_expdb` database contains all experiment-related data: datasets, tasks, flows (implementations), runs, evaluations, and studies.
The "expdb" part stands for "experiment database", the name used in [Joaquin Vanschoren's thesis](https://research.kuleuven.be/portal/en/project/3E061119).

Some remarks which apply generally:

 - `datetime` fields are in format (`YYYY-MM-DD hh:mm:ss`).
 - some `varchar` columns in production only have a very limited set of values. If the description says "one of.." it denotes only those values are present in the database in production.

There are a few tables which never were or no longer are in use.
They will be removed and so are not documented here. They are: `data_quality_interval`, `feature_quality`, `output_data` (only present on the test server), `algorithm` and `algorithm_quality`.
For more information, see [server-api#165](https://github.com/openml/server-api/issues/165).

---

## Datasets

### dataset

Stores dataset metadata including source, format, licensing, and upload information.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| did | int unsigned | No | auto_increment | | Primary key (dataset ID). | 42 |
| uploader | mediumint unsigned | Yes | NULL | [openml.users.id](openml.md#users) | User who uploaded the dataset. | 2 |
| source | int unsigned | Yes | NULL | | ID of the original source dataset if derived. Used only rarely. | 3 |
| name | varchar(128) | No | | | Dataset name. | iris |
| version | varchar(64) | No | | | Version string, displayed on the dataset page. | 3 |
| version_label | varchar(128) | Yes | NULL | | Human-readable label. | tabular-ml-iid-study-0.0.1 |
| format | varchar(64) | No | 'arff' | | File format, one of: ARFF, Sparse_ARFF, CSV, "CSV, MAT", txt, Rimage | ARFF |
| creator | text | Yes | NULL | | Original creator(s) of the dataset. | "Jason", "G. Davies, A. Horne" |
| contributor | text | Yes | NULL | | People who contributed to the current version (e.g., formatting). | "A. Dent", "The Data Institute" |
| collection_date | varchar(128) | Yes | NULL | | When the data was originally collected, in any format. | "1980", "2024-10-30", "2022, 5 May" |
| upload_date | datetime | No | | | When the dataset was uploaded to OpenML. | 2014-04-06 23:19:20 |
| language | varchar(128) | Yes | NULL | | Language of the dataset content. | "En", "Dutch" |
| licence | varchar(64) | No | 'Public' | | License under which the dataset is shared. | Public |
| citation | text | Yes | NULL | | How to cite this dataset, sometimes a link to the policy. | Bareiss, E. Ray, & \[...\] Proceedings of \[...\] |
| collection | varchar(64) | Yes | NULL | | Collection the dataset belongs to. Not used. | NULL |
| url | mediumtext | No | | | URL to download the dataset file. Most often links to OpenML, but not always. | https://openml.org/data/download/22126628/test.arff |
| parquet_url | mediumtext | Yes | NULL | | *NOT IN PRODUCTION* URL to Parquet version of the dataset. | |
| isOriginal | enum('true','false') | Yes | NULL | | Whether this is an original dataset (not derived). | true |
| file_id | int | Yes | NULL | [openml.file.id](openml.md#file) | Reference to the uploaded file. | 60 |
| default_target_attribute | varchar(1024) | Yes | NULL | | Name of the default target column. Allows csv. | class |
| row_id_attribute | varchar(128) | Yes | NULL | | Name of the row identifier column. Allows csv. | id |
| ignore_attribute | varchar(128) | Yes | NULL | | Columns to ignore during modeling. Allows csv. | "animal", "'url_hash', 'query_id'" |
| paper_url | mediumtext | Yes | NULL | | URL to an associated publication. | https://arxiv.org/html/2402.55618v3 |
| visibility | varchar(128) | No | 'public' | | Visibility level (public, private, or friends). Note non-public visibility are currently not supported. | public |
| original_data_id | int | Yes | NULL | | ID of the original dataset this was derived from. | 23 |
| original_data_url | mediumtext | Yes | NULL | | URL to the original data source. | https://zenodo.org/record/322475/files/bike.arff  |
| update_comment | text | Yes | NULL | | Comment explaining the latest update. | fixed features |
| last_update | datetime | Yes | NULL | | Timestamp of the last update. | 2017-10-28 23:42:18 |


### dataset_description

Stores versioned descriptions for datasets.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| did | int unsigned | No | | [dataset.did](#dataset) | Dataset this description belongs to. | 42 |
| version | int unsigned | No | | | Description version number. | 2 |
| description | text | No | | | The dataset description text. | This dataset describes... |
| uploader | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who wrote this description. | 3 |

### dataset_status

Tracks the current status of the dataset.
The absence of an entry in this table for a dataset denotes that the dataset is "in preparation".
Rows are removed from this table to indicate transitions (deactivated -> activate)!
It does *not* provide a historical record of the dataset status.

Allowed transitions are (as defined by the PHP implementation):

 - in preparation -> activate
 - in preparation -> deactivated
 - deactivated -> activate

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| did | int unsigned | No | | [dataset.did](#dataset) | Dataset ID. | 42 |
| status | enum('active','deactivated') | No | | | Status value. | active |
| status_date | datetime | No | | | When the status was set. | 2022-04-10 11:10:42 |
| user_id | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who changed the status. | 1 |

### dataset_tag

User-assigned tags on datasets for categorization and search.
Note that historically, collections used tags (e.g., `study_14` indicates the dataset is linked to study 14).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int unsigned | No | | [dataset.did](#dataset) | Dataset ID. | 3 |
| tag | varchar(255) | No | | | Tag string. | Medicine, study_14 |
| uploader | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who added the tag. | 4 |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the tag was added. | 2018-11-04 08:57:17 |

### dataset_topic

Assigns topic labels to datasets.
Topics are displayed as tags on the web page.
This is the result of an experiment in 2021 to try categorize datasets to better facilitate search.
Topics have been added by automated analysis.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int unsigned | No | | [dataset.did](#dataset) | Dataset ID. | 5 |
| topic | varchar(255) | No | | | Topic label. | Health |
| uploader | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who assigned the topic. | 8111 |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the topic was assigned. | 2021-06-01 12:32:45 |

---

## Data Features and Qualities

### data_feature

Stores metadata and statistics for each feature (column) of a dataset, as computed by an evaluation engine.

!!! bug "What's going on?"

    We need more documentation for the computed columns `NumberOf*` and `ClassDistribution`.
    From just the database values, it's unclear what's going on.
    For example, 'nominal' features have their `NumberOfIntegerValues` column populated.


| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| did | int unsigned | No | | [dataset.did](#dataset) | Dataset ID. | 2 |
| index | int unsigned | No | | | Feature index (column position), 0-indexed. | 0 |
| evaluation_engine_id | int | No | | [evaluation_engine.id](#evaluation_engine) | Engine that computed the feature metadata. | 1 |
| name | varchar(64) | No | | | Feature name. | petal-width |
| data_type | varchar(64) | Yes | NULL | | Data type (numeric, nominal, string, date, unknown). | numeric |
| is_target | enum('true','false') | No | 'false' | | Whether this is the default target feature. | true |
| is_row_identifier | enum('true','false') | No | 'false' | | Whether this feature is a row ID. | false |
| is_ignore | enum('true','false') | No | 'false' | | Whether this feature should be ignored. | false |
| NumberOfDistinctValues | int | Yes | NULL | | Number of distinct values. | 14972 |
| NumberOfUniqueValues | int | Yes | NULL | | Number of values that appear exactly once. | 0 |
| NumberOfMissingValues | int | No | | | Count of missing values. | 124 |
| NumberOfIntegerValues | int | Yes | NULL | | Count of integer values. | |
| NumberOfRealValues | int | Yes | NULL | | Count of real-valued entries. | |
| NumberOfNominalValues | varchar(512) | No | | | Number of nominal categories (or distribution). | |
| NumberOfValues | int | No | | | Total number of values. | |
| MaximumValue | int | Yes | NULL | | Maximum value (for numeric features). | |
| MinimumValue | int | Yes | NULL | | Minimum value (for numeric features). | |
| MeanValue | int | Yes | NULL | | Mean value (for numeric features). | |
| StandardDeviation | int | Yes | NULL | | Standard deviation (for numeric features). | |
| ClassDistribution | text | Yes | NULL | | Only for nominal features, otherwise '[]'. See below. | [["?","T"],[[7, 99, 586, 0, 67, 2],[1, 0, 98, 0, 0, 38]]] |

ClassDistribution is `[]` for all features except nominal ones, and only populated if the dataset has a target feature that is also nominal (note that a dataset can have multiple target features).
For nominal features, it is a U x C matrix where U is the number of unique values in the feature and C is the number of classes of the target feature of the dataset.
Each cell specifies how often the feature value occurs for the specific target value.
The behavior with multiple target features that are nominal is unspecified.

### data_feature_description

User-provided descriptions and ontology annotations for individual data features.
The table is empty in production (as of 2026-04-29).
This feature was added recently (2025ish) should be considered experimental.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| did | int unsigned | No | | [data_feature(did, index)](#data_feature) | Dataset ID. | 2 |
| index | int unsigned | No | | [data_feature(did, index)](#data_feature) | Feature index (column position, 0 indexed). | 0 |
| uploader | mediumint unsigned | No | | | User who added the description. | 1548 |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the description was added. | 2025-12-12 09:29:30 |
| description_type | enum('plain','ontology') | No | | | Type of description. | 'ontology' |
| value | varchar(256) | No | | | The description or ontology URI. | http://xmlns.com/foaf/0.1/#name |

### data_feature_value

Enumerates the distinct values of a feature (only for nominal features).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| did | int unsigned | No | | [data_feature(did, index)](#data_feature) | Dataset ID. | 2 |
| index | int unsigned | No | | [data_feature(did, index)](#data_feature) | Feature index. | 3 |
| value | varchar(256) | No | | | A distinct value of the feature. | 'tulip' |

### data_quality

Stores computed quality measures (meta-features) for datasets, such as number of instances or entropy.
Measures are computed by an evaluation engine.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| data | int unsigned | No | 0 | [dataset.did](#dataset) | Dataset ID. | 2 |
| quality | varchar(128) | No | | [quality.name](#quality) | Name of the quality measure. | 'AutoCorrelation' |
| evaluation_engine_id | int | No | | [evaluation_engine.id](#evaluation_engine) | Engine that computed the quality. | 1 |
| value | varchar(128) | Yes | NULL | | Computed value. | 0.5 |
| description | text | Yes | NULL | | Additional description or notes. | |


### data_processed

Tracks whether a dataset has been processed by an evaluation engine (feature extraction, quality computation).
Note that this table is used with in-place edits. Retrying a failed will increment `num_tries`, not add a new row.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| did | int unsigned | No | | [dataset.did](#dataset) | Dataset ID. | 1 |
| evaluation_engine_id | int | No | | [evaluation_engine.id](#evaluation_engine) | Engine that processed the dataset. | 1 |
| user_id | int | No | | | User who triggered processing. | 1 |
| processing_date | datetime | No | | | When processing completed. | 2020-02-04 12:45:01 |
| error | text | Yes | NULL | | Error message if processing failed. | "keyword @relation expected, read Token[Id], line 1" |
| warning | text | Yes | NULL | | Warning messages from processing. Always NULL on prod. | NULL |
| num_tries | int | No | 1 | | Number of processing attempts. | 3 |


### quality

Defines the available dataset quality measures (meta-features) and their properties.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| name | varchar(128) | No | | | Primary key. Name of the quality measure. | AutoCorrelation |
| type | varchar(128) | No | 'DataProperty' | | Category, one of DataQuality, FeatureQuality, AlgorithmQuality. | FeatureQuality |
| formula | text | Yes | NULL | | Formula or computation method. Always NULL except for 1 row. | Calculated using... |
| description | text | Yes | NULL | | Human-readable description. | Average class difference between consecutive instances. |
| datatype | varchar(128) | No | 'undefined' | | Expected data type of the value. One of 'double', 'integer', 'undefined'. | |
| min | float | Yes | NULL | | Minimum possible value. | 0 |
| max | float | Yes | NULL | | Maximum possible value. | 1.0 |
| unit | varchar(32) | Yes | NULL | | Unit of measurement. | NULL |
| priority | int | No | 9999 | | Display priority (lower is higher priority). | 2 |
| showonline | enum('true','false') | No | | | Whether to show on the website. | true |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the quality was defined. | 2014-12-31 23:00:00 |


---

## Tasks

To more easily understand the way tasks are structured, we break down tasks into three components:

 - the task type: concept of what the task is (e.g., Supervised Classification) and the `task_type_inout` specifies the required and optional inputs and outputs for such a task. For example, a Supervised Classification task must have (among others) a target feature specified.
 - the estimation procedure: the experimental setup to evaluate model quality for the task (e.g., 10-fold Cross Validation)
 - the `task` together with its `task_inputs` specify concrete values for the task (e.g., 10-fold Cross Validation on Iris predicting Class).

For example, [task 59](https://www.openml.org/t/59) (10-fold Cross Validation on Iris) has the `task` row in the database (`task_id=59, ttid=1, ...`):

 1. It is of task type 1, Supervised Classification (from resolving its `ttid` column against the `task_type` table).
 2. When the task was created, the creator had to specify the following input since they are `required` for the task type as dictated by `task_type_inout`:
    - source data: to which dataset is the task linked?
    - estimation procedure: what is the experimental setup for the runs?
    - target feature: what is the target to predict?
 3. It could have optionally also specified the following properties, as indicated by the `task_type_inout` table: cost matrix, custom testset, evaluation measures.
 4. The `task_inputs` table is to specify what the corresponding values are for this task. E.g., the row with input "source\_data" has value "61" specifying that dataset 61 is used. It similarly defines the estimation procedure, target feature, and also the optional input of "evaluation measure". That is to say, `task_inputs` primarily references other tables.
 5. The estimation procedure required by the task type, and given a value in `task_inputs`, must correspond to an entry in the `estimation_procedure` table. E.g., if we find (`estimation_procedure`, `1`) as a task input, we know it is 10-fold Cross Validation (the row with `id=1` in `estimation_procedure`).
 6. `task_type_inout` further specifies that they expect `output` of experiments of the task may contain: evaluation measures, model, predictions. This is not directly used for tasks, but rather for runs.

So there are contraints from the `task_inputs` table to multiple other tables (`dataset`, `estimation_procedure`, ...) that are not explicitly present in the database.
The `task_inputs` is also expected to be populated with entries for each task dependent on the respective input defined by the `task_type_inout` table.
The `estimation_procedure_type` table provides general descriptions for procedures (such as Hold out), they are matched by name even though the relationship is not explicit in the database.

### task_type

Defines the types of machine learning tasks available (e.g., classification, regression).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| ttid | int | No | auto_increment | | Primary key (task type ID). | 1 |
| name | varchar(128) | No | | | Task type name. | Supervised Classification |
| description | text | No | | | Description of the task type. | Predict the value of a nominal feature given the other features. |
| creator | varchar(128) | No | | | Who defined this task type. | "Alice Smith, John Hickey" |
| contributors | text | Yes | NULL | | Additional contributors. | "Piet Houten, Betty Boss" |
| creationDate | datetime | No | | | When the task type was created. | 2017-09-28 11:23:09 |

### task_type_inout

Defines the input and output specifications for each task type.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| ttid | int | No | | [task_type.ttid](#task_type) | Task type ID. | 1 |
| name | varchar(64) | No | | | Name of the input/output parameter. See note. | source_data |
| type | varchar(64) | No | | | Data type of the parameter, from [task_io_types](#task_io_types). | String, "Estimation Procedure" |
| io | enum('input','output') | No | | | Whether this is an input or output. | input |
| requirement | enum('required','optional','hidden') | No | | | Whether this parameter is required. | required |
| description | varchar(256) | No | | | Description of the parameter. | "This input is required to foo the bar." |
| order | int | No | | | Display order used by the frontend. | 29 |
| api_constraints | text | Yes | NULL | | API-level constraints on this parameter as JSON. | See below. |
| template_api | text | Yes | NULL | | Template for API representation. | See below. |
| template_search | text | Yes | NULL | | Template for search representation. | See below. |


The `api_constraints`, `template_api` and `template_search` columns contain values that are used by PHP to help format responses.

The `api_constraints` contains JSON with optionally some special instructions:
```json
{
"data_type": "string",
"select": "name",
"from": "data_feature",
"where": "did = '[INPUT:source_data]' AND data_type = 'nominal'"
}
```
Production uses the following directives:

 - `[INPUT:source_data]`: look up the value of `task_inputs.value` where `input="source_data"` and `task_id` matches the task.
 - `[TASK:ttid]`: look up the valud of `task.ttid` for that task.

The `template_api` contains XML instead:
```xml
 <oml:estimation_procedure>
<oml:id>[INPUT:estimation_procedure]</oml:id>
<oml:type>[LOOKUP:estimation_procedure.type]</oml:type>
<oml:data_splits_url>[CONSTANT:base_url]api_splits/get/[TASK:id]/Task_[TASK:id]_splits.arff</oml:data_splits_url>
<oml:parameter name="number_repeats">[LOOKUP:estimation_procedure.repeats]</oml:parameter>
<oml:parameter name="number_folds">[LOOKUP:estimation_procedure.folds]</oml:parameter>
<oml:parameter name="percentage">[LOOKUP:estimation_procedure.percentage]</oml:parameter>
<oml:parameter name="stratified_sampling">[LOOKUP:estimation_procedure.stratified_sampling]</oml:parameter>
</oml:estimation_procedure>
```
Additionally contains the directives:

 - `[LOOKUP:*]`: looks up the `TABLE.row` value that are associated with the task.
 - `[CONSTANT:*]`: look up constants configured in PHP, not in the database.

Finally, the `template_search` contains JSON again:
```json
{
  "name": "Dataset(s)",
  "autocomplete": "commaSeparated",
  "datasource": "expdbDatasetVersion()",
  "placeholder": "(*) include all datasets"
}
```

The `expdbDatasetVersion()` function is no longer used.

### task_io_types

Defines the valid types for task inputs and outputs.
Used in the `task_type_inout` table.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| name | varchar(64) | No | | | Primary key. Type name. | String  |
| description | text | No | | | Description of this I/O type. | A string, possibly contains csv values. |

### task

Represents a specific machine learning task.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| task_id | int | No | auto_increment | | Primary key. | 59 |
| ttid | int | No | | [task_type.ttid](#task_type) | Task type. | 1 |
| creator | mediumint unsigned | Yes | NULL | [openml.users.id](openml.md#users) | User who created the task. | 1 |
| creation_date | datetime | Yes | NULL | | When the task was created. | 2014-11-02 03:12:15 |
| embargo_end_date | datetime | Yes | NULL | | End date of any data embargo. | 2025-10-30 23:52:28 |

### task_inputs

Stores the input parameter values for a specific task instance.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| task_id | int | No | | [task.task_id](#task) | Task ID. | 59 |
| input | varchar(64) | No | | | Input parameter name. | source_data |
| value | text | No | | | Input parameter value. | 61 |

Valid `input` values depend on the `task_type_inout` for the `task_type` that's specified in the `task`.

### task_tag

User-assigned tags on tasks.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int | No | | [task.task_id](#task) | Task ID. | 59 |
| tag | varchar(255) | No | | | Tag string. | uci |
| uploader | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who added the tag. | 2 |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the tag was added. | 2022-10-09 17:18:19 |

### estimation_procedure_type

Defines the types of estimation procedures (e.g., cross-validation, holdout).
Variations are defined in the `estimation_procedure` table.
E.g., this table describes "cross validation" and `estimation_procedure` describes `10-fold cross validation`, `5-fold cross validation`, and so on.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| name | varchar(64) | No | | | Primary key. Procedure type name. | crossvalidation |
| description | text | No | | | Description of the procedure type. | a process where the dataset is divided into folds, ... |

### estimation_procedure

Defines specific estimation procedure configurations used in tasks.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int | No | auto_increment | | Primary key. | 1 |
| ttid | int | No | | [task_type.ttid](#task_type) | Task type this procedure applies to. | 1 |
| name | varchar(128) | No | | | Procedure name. | 10-fold cross validation |
| type | enum('crossvalidation','leaveoneout','holdout','holdout_ordered','bootstrapping','subsampling','testthentrain','holdoutunlabeled','customholdout','testontrainingdata') | No | | | Procedure type. | crossvalidation |
| repeats | int | Yes | NULL | | Number of repetitions. | 1 |
| folds | int | Yes | NULL | | Number of folds. | 10 |
| samples | enum('false','true') | No | 'false' | | Whether learning curve samples are used. | false |
| percentage | int | Yes | NULL | | Train/test split percentage. | NULL |
| stratified_sampling | enum('true','false') | Yes | NULL | | Whether stratified sampling is used. | true |
| custom_testset | enum('true','false') | No | 'false' | | Whether a custom test set is provided. | false |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the procedure was created. | 2020-02-20 20:02:20 |

---

## Flows (Implementations)
The database uses historical names 'implementation' for a flow and 'algorithm' for ??.

### implementation

Stores machine learning flows (algorithms/pipelines) that can be executed on tasks.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int | No | auto_increment | | Primary key (flow ID). |  1 |
| fullName | varchar(1024) | No | | | Full qualified name (name + version). | sklearn.tree.DecisionTreeClassifier(1) |
| uploader | mediumint unsigned | Yes | NULL | [openml.users.id](openml.md#users) | User who uploaded the flow. | 2 |
| name | varchar(1024) | No | | | Flow name. | sklearn.tree.DecisionTreeClassifier |
| custom_name | varchar(256) | Yes | NULL | | User-defined display name. | Tree |
| class_name | varchar(256) | Yes | NULL | | Class name in the source library. | nl.liacs.subdisc.SubgroupDiscovery |
| version | int | No | | | Internal version number. | 1 |
| external_version | varchar(128) | No | | | Version string from the source library. | "sklearn=0.12.3,numpy=0.22.1" |
| creator | varchar(128) | Yes | NULL | | Original creator of the algorithm. | Arlo Knoppen |
| contributor | text | Yes | NULL | | Additional contributors. | "Marcel Alder" |
| uploadDate | datetime | No | | | When the flow was uploaded. | 2015-12-21 18:28:38 |
| licence | varchar(64) | Yes | NULL | | License. | public domain |
| language | varchar(128) | Yes | NULL | | Language the description is written in. Sometimes used to specify programming language instead. | English |
| description | text | Yes | NULL | | Short description. | Common Decision Tree algorithm |
| fullDescription | text | Yes | NULL | | Full description. | This algorithm partitions the data... |
| installationNotes | text | Yes | NULL | | Installation instructions. Not really used. | Runs on OpenML |
| dependencies | text | Yes | NULL | | Required dependencies. | mlr\_2.3 |
| implements | varchar(128) | Yes | NULL | | Algorithm or standard this flow implements. Seems to be legacy | build\_cpu\_time |
| binary_file_id | int | Yes | NULL | | File ID of the compiled binary. | 32 |
| source_file_id | int | Yes | NULL | | File ID of the source code. | 33 |
| visibility | varchar(128) | No | 'public' | | Visibility level. One of 'public' or 'private' | public |
| citation | text | Yes | NULL | | How to cite this flow. Only used once. | "A. Boo et al., Journal of ..." |



### implementation_component

Defines parent-child relationships between flows (e.g., a pipeline containing sub-flows).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| parent | int | No | | [implementation.id](#implementation) | Parent flow ID. | 1 |
| child | int | No | | [implementation.id](#implementation) | Child (component) flow ID. | 2 |
| identifier | varchar(1024) | Yes | NULL | | Role or name of the component within the parent. | PCA, scaler |

### implementation_tag

User-assigned tags on flows.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int | No | | [implementation.id](#implementation) | Flow ID. | 2 |
| tag | varchar(255) | No | | | Tag string. | Verified\_Supervised\_Classification |
| uploader | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who added the tag. | 2 |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the tag was added. | 2020-06-08 09:20:28 |

### input

Defines the hyperparameters (input parameters) of a flow.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int | No | auto_increment | | Primary key. | 2 |
| implementation_id | int | No | | [implementation.id](#implementation) | Flow this parameter belongs to. | 1 |
| name | varchar(512) | Yes | NULL | | Parameter name. | C |
| description | text | Yes | NULL | | Parameter description. | Regularization parameter. |
| dataType | varchar(255) | Yes | NULL | | Expected data type. | float |
| defaultValue | text | Yes | NULL | | Default value. | 1.0 |
| recommendedRange | text | Yes | NULL | | Recommended value range. | 10e-3 to 10e3 |

---

## Setups

Setups are really part of a run, they specifically describe the algorithm (flow) configuration used in the run.
They are not a separate entity. Each row in the `run` table refers to a setup. A setup may be shared by multiple runs.


### algorithm_setup

Represents a specific configuration (hyperparameter setting) of a flow, including nested component setups.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| sid | int unsigned | No | auto_increment | | Primary key (setup ID). | 1  |
| parent | int unsigned | No | | | Parent setup ID (for nested components). | NULL |
| implementation_id | int | No | | [implementation.id](#implementation) | Flow this setup configures. | 3 |
| algorithm | varchar(128) | Yes | NULL | | Algorithm name. Always NULL is prod! | NULL |
| role | varchar(64) | No | 'Learner' | | Role of this component (e.g., Learner, Preprocessor). | learner |
| isDefault | enum('true','false') | Yes | 'false' | | Whether this is the default setup. | true |
| algorithm_structure | varchar(64) | Yes | NULL | | Not sure. Always NULL in prod. | NULL |
| setup_string | text | Yes | NULL | | Serialized setup string. Can aid reproducing the run. | "weka.classifiers.trees.J48 -- -C 0.25 -M 2" |

### input_setting

Stores the actual hyperparameter values for a specific setup.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| setup | int unsigned | No | 0 | [algorithm_setup.sid](#algorithm_setup) | Setup ID. | 1 |
| input | varchar(128) | No | | | Parameter name. Only old setups have this. | 428_I |
| input_id | int | No | | [input.id](#input) | Reference to the parameter definition. | 4124 |
| value | varchar(2048) | No | | | Parameter value. | 1000, gini |

### setup_tag

User-assigned tags on setups.
Setups can not really be assigned by users, only admins. Runs should be tagged by users.

These tags are only used in the filtering of `/setups/list`, they are not returned with a `setup` or `run`.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int unsigned | No | | [algorithm_setup.sid](#algorithm_setup) | Setup ID. | 42 |
| tag | varchar(255) | No | | | Tag string. | test_setup |
| uploader | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who added the tag. | 2 |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the tag was added. | 2024-12-01 23:04:57 |

### setup_differences

Precomputed pairwise differences between setups on specific tasks.
Not entirely sure what this means, but seems to be out of use (last setup included is from a run in 2019).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| sidA | int | No | | | First setup ID. | 2 |
| sidB | int | No | | | Second setup ID. | 3 |
| task_id | int | No | | | Task ID. | 1245 |
| task_size | int | No | | | Size of the task dataset. | 100000 |
| differences | int | No | | | ??? | 812987 |

---

## Runs and Evaluations

### run

Represents the execution of a flow setup on a task.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| rid | int unsigned | No | auto_increment | | Primary key (run ID). |  2 |
| uploader | mediumint unsigned | Yes | NULL | [openml.users.id](openml.md#users) | User who uploaded the run. | 16 |
| setup | int unsigned | No | 0 | [algorithm_setup.sid](#algorithm_setup) | Setup (hyperparameter configuration) used. | 2894 |
| task_id | int | Yes | NULL | [task.task_id](#task) | Task the run was executed on. | 284 |
| start_time | datetime | Yes | NULL | | When the run started. | 2018-07-31 10:57:42 |
| error_message | text | Yes | NULL | | Error message if the run failed. | "weka.classifiers.bayes.HNB: Cannot handle numeric attributes!" |
| run_details | text | Yes | NULL | | Additional run details or logs. Not really used. | "Custom:Hyperparameter"  |
| visibility | varchar(128) | No | 'public' | | Visibility level, 'public' or 'private'. | public |

### run_evaluated

Tracks whether a run has been evaluated by an evaluation engine.
Currently only one evaluation engine is evaluating runs.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| run_id | int unsigned | No | | [run.rid](#run) | Run ID. | 24 |
| evaluation_engine_id | int | No | | [evaluation_engine.id](#evaluation_engine) | Engine that evaluated the run. | 1 |
| user_id | int | No | | | User who triggered evaluation. | 381 |
| evaluation_date | datetime | No | | | When evaluation completed. | 2024-02-04 08:09:27 |
| error | text | Yes | NULL | | Error message if evaluation failed. | "Index 1 out of bounds for length 1" |
| warning | text | Yes | NULL | | Warning messages from evaluation. | "Inconsistent Evaluation score: ..." |
| num_tries | int | No | 1 | | Number of evaluation attempts. | 1 |

### runfile

Stores metadata about files associated with a run (e.g., predictions, model files).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| source | int unsigned | No | | [run.rid](#run) | Run ID. | 28 |
| field | varchar(128) | No | | | File field name (e.g., predictions, model serialized). | predictions |
| name | varchar(128) | No | | | Original filename. | weka_generated_run5258986433356798974.xml |
| format | varchar(128) | No | | | File format. | xml |
| upload_time | datetime | Yes | NULL | | When the file was uploaded. | 2017-05-29 19:28:56 |
| file_id | int | No | | [openml.file.id](openml.md#file) | Reference to the file record. | 152 |

### run_tag

User-assigned tags on runs.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int unsigned | No | | [run.rid](#run) | Run ID. | 1521 |
| tag | varchar(255) | No | | | Tag string. | micro_benchmark |
| uploader | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who added the tag. | 124 |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the tag was added. | 2024-10-24 22:58:18 |

### input_data

Records the input datasets used by a run.
Used by PHP, but arguably they could use the relationship run->task->task_inputs->"source_data" instead.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| run | int | No | | | Run ID. | 21 |
| data | int | No | | | Dataset ID. | 42 |
| name | varchar(128) | No | 'inputdata' | | Always 'dataset' | dataset |

### evaluation_engine

Defines the evaluation engines that compute metrics on runs and datasets.
Currently only has one row, as we only ever used on engine in production.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int | No | auto_increment | | Primary key. | 1 |
| name | varchar(256) | No | | | Engine name. | weka_engine |
| description | text | No | | | Engine description. | "Default OpenML evaluation engine" |

### math_function

Defines evaluation metrics (e.g., accuracy, AUC, RMSE) and their properties.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int | No | auto_increment | | Primary key. | 1 |
| name | varchar(64) | No | | | Metric name (unique). | EuclidianDistance |
| functionType | varchar(128) | No | 'EvaluationFunction' | | Type of function. One of Metric, KernelFuction, or EvaluationFuction | Metric |
| min | varchar(64) | No | | | Minimum possible value. | 0 |
| max | varchar(64) | No | | | Maximum possible value. | '' |
| unit | varchar(64) | No | | | Unit of measurement. | seconds, bytes |
| higherIsBetter | varchar(16) | Yes | NULL | | Whether higher values indicate better performance. | true, Yes, 1, False |
| description | text | Yes | NULL | | Description of the metric. | "The area under the ROC..." |
| source_code | text | No | | | Source code or formula. | "public double truePositiveRate(..." |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the function was defined. | 2024-04-19 23:51:52 |

### evaluation

Stores aggregated evaluation results for a run (one value per metric).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| source | int unsigned | No | | [run.rid](#run) | Run ID. | 1 |
| function_id | int | No | | [math_function.id](#math_function) | Evaluation metric. | 4  |
| evaluation_engine_id | int | No | | [evaluation_engine.id](#evaluation_engine) | Engine that computed the evaluation. | 1 |
| value | double | Yes | NULL | | Aggregated metric value. | 0.839 |
| stdev | double | Yes | NULL | | Standard deviation across folds/repeats. | 0.06 |
| array_data | text | Yes | NULL | | Per-class or detailed results as array. | "[0.0,0.99113,0.898048,0.874862,0.791282,0.807343,0.820674]" |

### evaluation_fold

Stores per-fold evaluation results for a run.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| source | int unsigned | No | | [run.rid](#run) | Run ID. | 12 |
| function_id | int | No | | [math_function.id](#math_function) | Evaluation metric. | 4 |
| evaluation_engine_id | int | No | | [evaluation_engine.id](#evaluation_engine) | Engine that computed the evaluation. | 1 |
| fold | int unsigned | No | 0 | | Fold number. | 0 |
| repeat | int unsigned | No | 0 | | Repeat number. | 0 |
| value | double | Yes | NULL | | Metric value for this fold/repeat. | 0.5 |
| array_data | text | Yes | NULL | | Per-class or detailed results as array. | "[0.4, 0.6]" |

### evaluation_sample

Stores per-sample evaluation results (for learning curves).
Evaluation samples seem to be part of a run upload, but might not be able to be retrieved with the current PHP API.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| source | int unsigned | No | | [run.rid](#run) | Run ID. | 12 |
| function_id | int | No | | [math_function.id](#math_function) | Evaluation metric. | 4 |
| evaluation_engine_id | int | No | | [evaluation_engine.id](#evaluation_engine) | Engine that computed the evaluation. | 1 |
| repeat | int unsigned | No | 0 | | Repeat number. | 0 |
| fold | int unsigned | No | 0 | | Fold number. | 0 |
| sample | int unsigned | No | 0 | | Sample index. | 0 |
| sample_size | int | No | | | Number of training instances in this sample. | 100 |
| value | double | Yes | NULL | | Metric value for this sample. | 0.5 |
| array_data | text | Yes | NULL | | Per-class or detailed results as array. | "[0.4,0.6]" |

### trace

Stores optimization traces (e.g., hyperparameter search iterations) for a run.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| run_id | int unsigned | No | | [run.rid](#run) | Run ID. | 2 |
| evaluation_engine_id | int | No | 1 | [evaluation_engine.id](#evaluation_engine) | Engine that evaluated the trace. | 1 |
| repeat | int | No | | | Repeat number. | 0 |
| fold | int | No | | | Fold number. | 0 |
| iteration | int | No | | | Iteration number in the optimization. | 0 |
| setup_string | text | No | | | Hyperparameter configuration tried. | '{"parameter_minNumObj":"1","parameter_confidenceFactor":"0.1"}' |
| evaluation | varchar(265) | No | | | Evaluation result for this iteration. | 94.12 |
| selected | enum('true','false') | No | | | Whether this was the selected configuration. | true |

---

## Studies

Studies have historically been in flux, but they are generally collections of objects (e.g., tasks).
One mayor change during OpenML's lifetime was in how those collections were defined, which happened around 2019.
Nowadays there are dedicated tables (e.g., study_task) to make the connection between a study and its task.
Historically, what is now referred to as a "legacy study", this association was achieved through tags.
E.g., all tasks with tag `study_14` would be considered part of `study_14`.
Some studies are still defined this way, and migration of these studies to new-style studies are planned.
The Python-based REST API will not support legacy style studies (hence the data migration needs to occur to make the legacy studies usable with the new API).

The current use is that "benchmark suite" refers to a collection of tasks and a "benchmark study" refers to a collection of runs.
Both are found in the "study" table. It is likely we drop this distinction in the future in favor of a more general "collection".

### study

Represents a collection of runs or tasks, used for benchmarking and reproducibility.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int | No | auto_increment | | Primary key (study ID). | 2 |
| alias | varchar(32) | Yes | NULL | | Short unique alias for the study. | automl_benchmark |
| main_entity_type | enum('run','task') | No | 'run' | | Whether the study collects runs or tasks. | tasks |
| benchmark_suite | int | Yes | NULL | [study.id](#study) | Reference to a task study used as benchmark suite. | 2 |
| name | varchar(256) | No | | | Study name. | "A friendly benchmarking suite for AutoML systems" |
| description | text | No | | | Study description. | "See also JMLR..." |
| visibility | varchar(64) | No | 'public' | | Visibility level. Only ever 'public' | public |
| status | enum('in_preparation','active','deactivated') | No | 'in_preparation' | | Current status. | active |
| creation_date | datetime | No | | | When the study was created. | 2021-02-04 20:48:58|
| creator | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who created the study. | 3 |
| legacy | enum('y','n') | No | 'y' | | Whether this is a legacy study. | y |


### study_tag

Tags applied to studies, with optional time windows and access control.
It is unclear why this table has a different design than the other tag tables, but it likely has to do with the "legacy" study setup.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| study_id | int | No | | [study.id](#study) | Study ID. | 28 |
| tag | varchar(255) | No | | | Tag string. | published, jmlr |
| window_start | datetime | Yes | NULL | | Start of the tag's validity window. | 2020-01-01 12:23:42 |
| window_end | datetime | Yes | NULL | | End of the tag's validity window. | 2021-04-11 19:54:24 |
| write_access | enum('private','public') | No | 'private' | | Who can add this tag. | private |

### run_study

A join table for the "new" style studies.
Associates runs with studies (many-to-many).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| study_id | int | No | | [study.id](#study) | Study ID. | 2 |
| run_id | int unsigned | No | | [run.rid](#run) | Run ID. |  102984 |
| uploader | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who added the run to the study. | 1815 |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the run was added. | 2024-05-12 23:10:54 |

### task_study

A join table for the "new" style studies.
Associates tasks with studies (many-to-many).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| study_id | int | No | | [study.id](#study) | Study ID. | 5 |
| task_id | int | No | | [task.task_id](#task) | Task ID. | 18257 |
| uploader | mediumint unsigned | No | | [openml.users.id](openml.md#users) | User who added the task to the study. | 12 |
| date | timestamp | No | CURRENT_TIMESTAMP | | When the task was added. | 2022-04-28 08:28:49 |

---

## Community

The `awarded_badges`, `likes`, `downvotes` and `downvote_reasons` tables are not currently in use.
They may be added back with the new frontend (except for `awarded_badges`).

### likes

Records user likes on datasets, flows, runs, or other entities.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| lid | int | No | auto_increment | | Unique ID. | 1 |
| knowledge_type | varchar(1) | No | | | Entity type code (e.g., 'd' for dataset). | d, f, r, t|
| knowledge_id | int | No | | | Entity ID. | 20248 |
| user_id | mediumint | No | | | User who liked the entity. | 241 |
| time | timestamp | No | CURRENT_TIMESTAMP | | When the like was recorded. | 2019-09-08 17:47:57 |

### downvotes

Records user downvotes on entities with a reason.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| did | int | No | auto_increment | | Unique ID. | |
| knowledge_type | varchar(1) | No | | | Entity type code. | |
| knowledge_id | int | No | | | Entity ID. | |
| user_id | mediumint | No | | | User who downvoted. | |
| reason | int | No | | | Reason for the downvote (references downvote_reasons). | |
| time | timestamp | No | CURRENT_TIMESTAMP | | When the downvote was recorded. | |
| original | tinyint | No | 0 | | Whether this is the original downvote (vs. an update). | |

### downvote_reasons

Defines the reasons for downvoting an entity.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| reason_id | int | No | auto_increment | | Primary key. | |
| description | varchar(256) | No | | | Description of the reason. | |

### downloads

Tracks download counts per user and entity.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| did | int | No | auto_increment | | Unique ID. | |
| knowledge_type | varchar(1) | No | | | Entity type code. | |
| knowledge_id | int | No | | | Entity ID. | |
| user_id | mediumint | No | | | User who downloaded. | |
| count | smallint | No | 1 | | Number of downloads. | |
| time | timestamp | No | CURRENT_TIMESTAMP | | Last download time. | |


---

## Miscellaneous

The `notebook` and `pdnresults` are no longer in use.

### schedule

Defines scheduled experiment jobs to be executed.
Seems to be out of use since 2017.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| sid | int | No | | | Setup ID. | |
| task_id | int | No | | | Task ID to run. | |
| experiment | varchar(128) | No | | | Experiment identifier. | |
| active | enum('true','false') | No | 'true' | | Whether the schedule is active. | |
| last_assigned | datetime | Yes | NULL | | When this job was last assigned to a worker. | |
| ttid | int | No | | | Task type ID. | |
| dependencies | varchar(128) | No | | | Dependency identifiers. | |
| setup_string | text | No | | | Serialized setup configuration. | |

### kaggle

Maps OpenML datasets to Kaggle competitions or datasets.
Defined by hand in collaboration with Kaggle.
Only used by the frontend.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| dataset_id | int | Yes | NULL | | OpenML dataset ID. | 6 |
| kaggle_link | varchar(500) | Yes | NULL | | URL to the Kaggle page. | https://www.kaggle.com/datasets/nishan192/letterrecognition-using-svm |
