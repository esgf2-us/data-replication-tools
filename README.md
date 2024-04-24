# Data Replication Tools

This repository containes Python scripts designed to facilitate the replication of 7.3 PB of CMIP5 and CMIP6 climate data from Lawrence Livermore National Laboratory (LLNL) to Argonne National Laboratory (ANL) and Oak Ridge National Laboratory (ORNL). The climate data's location at LLNL is provided as a list of 2291 directory paths (128 CMIP5 paths and 2163 CMIP6 paths) on the [LLNL ESGF (Open)](https://app.globus.org/file-manager?origin_id=1889ea03-25ad-4f9f-8110-1ce8833a9d7e) guest collection.

The scripts handle the submission of Globus transfers and monitor their status and transfer events. The status of transfers and transfer events is stored in a local PostgreSQL database, which is publicly accessible via the [Globus Dashboard - ESGF Replication](https://dashboard.globus.org/esgf/).

## Database Setup
The scripts utilize [SQLAlchemy](https://www.sqlalchemy.org/) to interface with a PostgreSQL database. Before running the scripts, it's necessary to set up the database and a user with appropriate privileges:
```
postgres=# create database migration;
postgres=# create user esgf with encrypted password 'esgf';
postgres=# grant all privileges on database migration to esgf;
```

## Data Replication Tools Setup
To get started, clone the repository and set up a Python virtual environment:
```
git clone https://github.com/esgf2-us/data-replication-tools.git
cd data-replication-tools/
python3 -mvenv venv
. venv/bin/activate
pip install -r requirements.txt
```
## Database Initialization 
Initialize the transfer table with the directory paths to be transferred recursively from LLNL to ANL and ORNL:
```
cat paths/* | python add.py
```

## Globus Authentication
Authentication with Globus is required for communication with the Globus Transfer API. The authentication flow utilizes OAuth2 to obtain access and refresh tokens. During the authentication process, users will be prompted for their Globus username and password. These tokens are essential for subsequent interactions with the Globus Transfer API and are securely stored for later use by the scripts.
```
cd src/
python replicate.py
```
Once the tokens are obtained and securrely stored in the local store, `~/.esgf-replication-native-client.cfg`, the scripts can utilize them for authenticated access to the Globus Transfer API.

## Cron jobs setup
To automate the replication process, add two crontab entries to run `replicate.py` and `get_events.py` every 10 to 30 minutes:
```
5,35 * * * * <path_to_the_local_repo>/data-replication-tools/src/replicate.sh
5-59/10 * * * * <path_to_the_local_repo>/data-replication-tools/src/replicate.sh
```
Feel free to adjust the timing according to your specific needs.
