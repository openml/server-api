from schemas.datasets.dcat import (
    DcatAPDataset,
    DcatAPDistribution,
    DcatAPIdentifier,
    DcatApWrapper,
    SpdxChecksum,
    XSDDateTime,
)
from schemas.datasets.openml import DatasetMetadata


def openml_dataset_to_dcat(metadata: DatasetMetadata) -> DcatApWrapper:
    checksum = SpdxChecksum(
        id_=metadata.md5_checksum,
        algorithm="md5",
        value=metadata.md5_checksum,
    )

    distribution = DcatAPDistribution(
        id_=metadata.url,
        format_=metadata.format_,
        access_url=metadata.original_data_url,
        checksum=DcatAPIdentifier(id_=checksum.id_),
        download_url=metadata.url,
        license_=metadata.licence,
    )

    dataset = DcatAPDataset(
        id_=metadata.id_,
        description=metadata.description,
        title=metadata.name,
        version=metadata.version,
        release_date=XSDDateTime(value_=metadata.upload_date),
        keyword=metadata.tag,
        distribution=[DcatAPIdentifier(id_=distribution.id_)],
        landing_page=[metadata.url],
    )
    return DcatApWrapper(
        graph_=[dataset, distribution, checksum],
    )
