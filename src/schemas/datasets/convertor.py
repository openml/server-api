from schemas.datasets.dcat import (
    DcatAPDataset,
    DcatAPDistribution,
    DcatApWrapper,
    SpdxChecksum,
)
from schemas.datasets.openml import DatasetMetadata


def openml_dataset_to_dcat(metadata: DatasetMetadata) -> DcatApWrapper:
    checksum = SpdxChecksum(
        id_=metadata.md5_checksum,
        algorithm="md5",
        checksumValue=metadata.md5_checksum,
    )

    distribution = DcatAPDistribution(
        id_=metadata.url,
        # issued=metadata.upload_date,
        format_=metadata.format_,
        # language=metadata.language,
        access_url=metadata.url,  # maybe openml.org/d/X instead?
        checksum=checksum.id_,
        download_url=metadata.url,
        license_=metadata.licence,
    )

    dataset = DcatAPDataset(
        id_=metadata.id_,
        description=metadata.description,
        title=metadata.name,
        version=metadata.version,
        release_date=metadata.upload_date,
        keyword=metadata.tag,
        distribution=[distribution],
        landing_page=[metadata.url],
    )
    return DcatApWrapper(
        graph_=[dataset, distribution, checksum],
    )
