class DatabaseConfig:
    config = {
        'connection_string': 'var/database/database.db',
        'start_date': '2023-10-01',
        'base_schema': './var/database/schema/base.json'
    }

class DatamartScrapperConfig:
    config = {
    'datamart_base_url': 'https://mpr.datamart.ams.usda.gov/services/v1.1/reports/',
    'being_pull_date': '2016-01-07',
    'retry_delay': 15
    }

'''
To add New Slug_ID
Add Slug ID to Schedule class in the correct time slot (To Add New Time Slot go to celery.worker.py)
Add the Slug_id and its configuration to the Slugs class
'''

class Schedule:

    schedule= {
        'AFTERNOON': ['0001','0002', '0003']
    }

class Slugs:
    slugs = {
        '0001': {
            'Variable1': 'Test',
            'Variable2': 2
        },
        '0002': {
            'Variable1': 'Test',
            'Variable2': 2
        },
    }