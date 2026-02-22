from app.adapters.dummy_adapter import DummyAdapter

class ModelAdapterFactory:
    def get_adapter(self, model_version_id: int) :
        
        return DummyAdapter()