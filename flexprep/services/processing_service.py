"""
Services providing core functionality.
"""

import logging

from flexprep import CONFIG
from flexprep.domain.prepare_processing import launch_pre_processing
from flexprep.domain.s3_utils import S3client

logger = logging.getLogger(__name__)


def process() -> None:
    logger.debug("Initialize Processing")

    s3_input = S3client().s3_client_input
    bucket_name = CONFIG.main.s3_buckets.input.name

    S3client().check_bucket(s3_input, bucket_name)

    s3_objects = s3_input.list_objects_v2(Bucket=bucket_name)

    launch_pre_processing(s3_objects)
