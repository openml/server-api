# openml Database

The `openml` database contains core platform tables for user management, file storage, access control, and community features.

## users

Stores registered user accounts and their authentication details.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | mediumint unsigned | No | auto_increment | | Primary key. | |
| ip_address | varchar(45) | No | | | IP address at registration. | |
| username | varchar(100) | No | | | Unique login name. | |
| password | varchar(255) | No | | | Hashed password. | |
| email | varchar(254) | No | | | Email address. | |
| activation_selector | varchar(255) | Yes | NULL | | Selector token for account activation. | |
| activation_code | varchar(255) | Yes | NULL | | Code for account activation. | |
| forgotten_password_selector | varchar(255) | Yes | NULL | | Selector token for password reset. | |
| forgotten_password_code | varchar(255) | Yes | NULL | | Code for password reset. | |
| forgotten_password_time | int unsigned | Yes | NULL | | Timestamp of password reset request. | |
| remember_selector | varchar(255) | Yes | NULL | | Selector token for "remember me" sessions. | |
| remember_code | varchar(255) | Yes | NULL | | Code for "remember me" sessions. | |
| created_on | int unsigned | No | | | Unix timestamp of account creation. | |
| last_login | int unsigned | Yes | NULL | | Unix timestamp of last login. | |
| active | tinyint unsigned | Yes | NULL | | Whether the account is activated. | |
| first_name | varchar(50) | Yes | NULL | | User's first name. | |
| last_name | varchar(50) | Yes | NULL | | User's last name. | |
| company | varchar(100) | No | | | Organization or affiliation. | |
| phone | varchar(20) | Yes | NULL | | Phone number. | |
| country | varchar(50) | No | | | Country of residence. | |
| image | varchar(128) | Yes | NULL | | Path to profile image. | |
| bio | text | No | | | User biography. | |
| core | enum('true','false') | No | 'false' | | Whether the user is a core team member. | |
| external_source | varchar(50) | Yes | NULL | | External authentication provider (e.g., OAuth). | |
| external_id | varchar(50) | Yes | NULL | | User ID from external authentication provider. | |
| session_hash | varchar(40) | Yes | NULL | | Hash for API session authentication. | |
| session_hash_date | timestamp | Yes | CURRENT_TIMESTAMP | | When the session hash was last generated. | |
| gamification_visibility | varchar(32) | No | 'show' | | Visibility setting for gamification badges. | |

## groups

Defines user groups for role-based access control.

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | mediumint unsigned | No | auto_increment | | Primary key. | |
| name | varchar(20) | No | | | Group name. | |
| description | varchar(100) | No | | | Description of the group's purpose. | |

## users_groups

Associates users with groups (many-to-many relationship).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | mediumint unsigned | No | auto_increment | | Primary key. | |
| user_id | mediumint unsigned | No | | [users.id](#users) | The user. | |
| group_id | mediumint unsigned | No | | [groups.id](#groups) | The group the user belongs to. | |

## file

Stores metadata about uploaded files (datasets, flows, predictions, etc.).

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| id | int | No | auto_increment | | Primary key. | |
| creator | int | No | | | User ID of the uploader. | |
| creation_date | datetime | No | | | When the file was uploaded. | |
| filepath | varchar(256) | No | | | Storage path on the server. | |
| filesize | int | No | | | File size in bytes. | |
| filename_original | varchar(256) | No | | | Original filename as uploaded. | |
| extension | varchar(16) | No | | | File extension (e.g., arff, csv). | |
| mime_type | varchar(32) | No | | | MIME type of the file. | |
| md5_hash | varchar(64) | No | | | MD5 checksum for integrity verification. | |
| type | enum('dataset','implementation','predictions','userimage','run_trace','run_uploaded_file','url','misc') | No | | | Category of the file. | |
| access_policy | enum('public','private','none','deleted') | No | 'public' | | Access control policy for the file. | |

## access

Controls access permissions for entities (datasets, flows, studies) that are not public.
**Access control as a feature is currently not used, but previously created private datasets remain private.**

| Column | Type | Optional | Default | References | Description | Example |
|--------|------|----------|---------|------------|-------------|---------|
| user_id | bigint | No | | | User or group ID granted access. | |
| group | enum('true','false') | No | | | Whether `user_id` refers to a group. | |
| type | enum('data','flow','study') | No | | | Type of entity this permission applies to. | |
| entity_id | bigint | No | | | ID of the entity being shared. | |


## deprecated tables
There are also `category` and `thread` tables which were designed for a forum feature but are not used.
The `meta_dataset` table is for requesting automated metadata set building, a feature which is not enabled.
