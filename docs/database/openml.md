# openml Database

The `openml` database contains core platform tables for user management, file storage, access control, and community features.

## users

Stores registered user accounts and their authentication details.
For a little while, the `username` and `email` were synonymous.


| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | mediumint unsigned | No | auto_increment | | Primary key. | 2 |
| ip_address | varchar(45) | No | | | IP address at registration. | 127.0.0.1 |
| username | varchar(100) | No | | | Unique login name. | foo@bar.com |
| password | varchar(255) | No | | | Hashed password. | - |
| email | varchar(254) | No | | | Email address. | foo@bar.com |
| activation_selector | varchar(255) | Yes | NULL | | Selector token for account activation. | |
| activation_code | varchar(255) | Yes | NULL | | Code for account activation. | |
| forgotten_password_selector | varchar(255) | Yes | NULL | | Selector token for password reset. | |
| forgotten_password_code | varchar(255) | Yes | NULL | | Code for password reset. | |
| forgotten_password_time | int unsigned | Yes | NULL | | Timestamp of password reset request. | |
| remember_selector | varchar(255) | Yes | NULL | | Selector token for "remember me" sessions. | |
| remember_code | varchar(255) | Yes | NULL | | Code for "remember me" sessions. | |
| created_on | int unsigned | No | | | Unix timestamp of account creation. | 1363880450 |
| last_login | int unsigned | Yes | NULL | | Unix timestamp of last login. | 1763344931 |
| active | tinyint unsigned | Yes | NULL | | Whether the account is activated through the confirmation email, 1 or 0. | 1 |
| first_name | varchar(50) | Yes | NULL | | User's first name. | Joaquin |
| last_name | varchar(50) | Yes | NULL | | User's last name. | van Rijn |
| company | varchar(100) | No | | | Organization or affiliation. | OpenML |
| phone | varchar(20) | Yes | NULL | | Phone number. Not in use. | 0000 |
| country | varchar(50) | No | | | Country of residence. No input validation was done. | rfr |
| image | varchar(128) | Yes | NULL | | Path to profile image. | https://www.openml.org/data//view/21794253/joa.jpeg |
| bio | text | No | | | User biography. | "My wonderful bio" |
| core | enum('true','false') | No | 'false' | | Whether the user is a core team member. | false |
| external_source | varchar(50) | Yes | NULL | | External authentication provider (e.g., OAuth). not in use | 0000 |
| external_id | varchar(50) | Yes | NULL | | User ID from external authentication provider. not in use |  0000 |
| session_hash | varchar(40) | Yes | NULL | | Hash for API session authentication. 32 digit hexidecimal | - |
| session_hash_date | timestamp | Yes | CURRENT_TIMESTAMP | | When the session hash was last generated. | 2024-10-20 20:18:54 |
| gamification_visibility | varchar(32) | No | 'show' | | Visibility setting for gamification badges. One of 'show' or 'hidden' | hidden |

## groups

Defines user groups for role-based access control.
Currently the database recognizes three groups: admins, normal users, and read-only users.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | mediumint unsigned | No | auto_increment | | Primary key. | 2 |
| name | varchar(20) | No | | | Group name. | members |
| description | varchar(100) | No | | | Description of the group's purpose. | normal read-write permissions |

## users_groups

Associates users with groups (many-to-many relationship).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | mediumint unsigned | No | auto_increment | | Primary key. | 2 |
| user_id | mediumint unsigned | No | | [users.id](#users) | The user. | 2 |
| group_id | mediumint unsigned | No | | [groups.id](#groups) | The group the user belongs to. | 2 |

## file

Stores metadata about uploaded files (datasets, flows, predictions, etc.).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int | No | auto_increment | | Primary key. | 1 |
| creator | int | No | | | User ID of the uploader. | 2 |
| creation_date | datetime | No | | | When the file was uploaded. | 2015-11-30 06:48:32 |
| filepath | varchar(256) | No | | | Storage path on the server. | dataset/api/dataset_1_anneal.arff |
| filesize | int | No | | | File size in bytes. | 143338 |
| filename_original | varchar(256) | No | | | Original filename as uploaded. | dataset_1_anneal.arff |
| extension | varchar(16) | No | | | File extension (e.g., arff, csv). | arff |
| mime_type | varchar(32) | No | | | MIME type of the file. | application/octet-stream |
| md5_hash | varchar(64) | No | | | MD5 checksum for integrity verification. | 43b29a3eb09e8fac9a8525c3c83abec8 |
| type | enum('dataset','implementation','predictions','userimage','run_trace','run_uploaded_file','url','misc') | No | | | Category of the file. | dataset |
| access_policy | enum('public','private','none','deleted') | No | 'public' | | Access control policy for the file. | public |


## deprecated tables
There are also `category` and `thread` tables which were designed for a forum feature but are not used.
The `meta_dataset` table is for requesting automated metadata set building, a feature which is not enabled.
The `access` table is not used, access constraints are currently handled by columns in the respective table (e.g., `dataset.visibility` for datasets).
