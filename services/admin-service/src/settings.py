from shared.config.settings import BaseServiceSettings


class AdminSettings(BaseServiceSettings):
    # Health-check URLs for sibling services
    chat_service_url: str = "http://chat-service:8000"
    uploader_service_url: str = "http://uploader-service:8000"
    doc_processing_service_url: str = "http://doc-processing-service:8000"
    embedding_service_url: str = "http://embedding-service:8000"
    indexing_service_url: str = "http://indexing-service:8000"


settings = AdminSettings()
