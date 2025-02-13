import os
import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Blueprint, Flask, jsonify, request
from mem0 import Memory
from qdrant_client import QdrantClient, models

# Cấu hình logging
def setup_logging(app):
    # Tạo thư mục logs nếu chưa tồn tại
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Cấu hình handler để ghi log vào file
    file_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=10240, 
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Cấu hình logging cho ứng dụng
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

load_dotenv()

app = Flask(__name__)
app.url_map.strict_slashes = False

# Thiết lập logging
setup_logging(app)

api = Blueprint("api", __name__, url_prefix="/v1")

config = {
    "llm": {
        "provider": "gemini",
        "config": {
            "model": "gemini-1.5-flash-8b",
            "temperature": 0.2,
            "max_tokens": 1500,
            "api_key": os.environ.get("GEMINI_API_KEY")
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": os.environ.get("QDRANT_HOST", "160.22.122.50"),
            "port": int(os.environ.get("QDRANT_PORT", 6333)),
            "collection_name": "mem0"
        },
    },
    "embeddings": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "api_key": os.environ.get("OPENAI_API_KEY")
        }
    }
}

# Thêm vào trước khi tạo memory
try:
    client = QdrantClient(host=config['vector_store']['config']['host'],
                         port=config['vector_store']['config']['port'])
    
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]
    collection_name = config['vector_store']['config']['collection_name']
    
    # Xóa collection cũ nếu tồn tại để tạo mới
    if collection_name in collection_names:
        app.logger.info(f"Deleting existing collection {collection_name}...")
        client.delete_collection(collection_name)
    
    app.logger.info(f"Creating new collection {collection_name}...")
    
    # Kích thước vector của OpenAI text-embedding-3-small là 1536
    VECTOR_SIZE = 1536
    
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE
        )
    )
    
    # Verify collection creation
    collection_info = client.get_collection(collection_name)
    app.logger.info(f"Collection created successfully. Info: {collection_info}")
    
except Exception as e:
    app.logger.error(f"Error setting up Qdrant collection: {str(e)}", exc_info=True)
    raise Exception(f"Failed to setup Qdrant collection: {str(e)}")

# Tạo memory object sau khi đã setup collection
try:
    memory = Memory.from_config(config)
    app.logger.info("Memory object created successfully")
except Exception as e:
    app.logger.error(f"Error creating Memory object: {str(e)}", exc_info=True)
    raise


@api.route("/memories", methods=["POST"])
def add_memories():
    try:
        body = request.get_json()
        app.logger.info(f"Received add memories request: {body}")
        
        # Kiểm tra OpenAI API key
        app.logger.info(f"Checking OpenAI API key: {'OPENAI_API_KEY' in os.environ}")
        
        # Thêm memory với logging chi tiết
        app.logger.info("Starting memory.add operation...")
        result = memory.add(
            body["messages"],
            user_id=body.get("user_id"),
            agent_id=body.get("agent_id"),
            run_id=body.get("run_id"),
            metadata=body.get("metadata", {}),  # Đảm bảo metadata không None
            filters=body.get("filters", {}),    # Đảm bảo filters không None
            prompt=body.get("prompt"),
        )
        
        app.logger.info(f"Memory add operation completed with full result: {result}")
        return jsonify(result)  # Đảm bảo trả về JSON response
    except Exception as e:
        app.logger.error(f"Error in add_memories: {str(e)}", exc_info=True)
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__,
            "error_details": repr(e)
        }), 400


@api.route("/memories/<memory_id>", methods=["PUT"])
def update_memory(memory_id):
    try:
        # Log thông tin request
        app.logger.info(f"Received update memory request for ID: {memory_id}")
        
        existing_memory = memory.get(memory_id)
        if not existing_memory:
            app.logger.warning(f"Memory not found: {memory_id}")
            return jsonify({"message": "Memory not found!"}), 400
        
        body = request.get_json()
        result = memory.update(memory_id, data=body["data"])
        
        # Log kết quả thành công
        app.logger.info(f"Successfully updated memory {memory_id}")
        return result
    except Exception as e:
        # Log lỗi
        app.logger.error(f"Error in update_memory: {str(e)}", exc_info=True)
        return jsonify({"message": str(e)}), 400


@api.route("/memories/search", methods=["POST"])
def search_memories():
    try:
        body = request.get_json()
        return memory.search(
            body["query"],
            user_id=body.get("user_id"),
            agent_id=body.get("agent_id"),
            run_id=body.get("run_id"),
            limit=body.get("limit", 100),
            filters=body.get("filters"),
        )
    except Exception as e:
        return jsonify({"message": str(e)}), 400


@api.route("/memories", methods=["GET"])
def get_memories():
    try:
        return memory.get_all(
            user_id=request.args.get("user_id"),
            agent_id=request.args.get("agent_id"),
            run_id=request.args.get("run_id"),
            limit=request.args.get("limit", 100),
        )
    except Exception as e:
        return jsonify({"message": str(e)}), 400


@api.route("/memories/<memory_id>/history", methods=["GET"])
def get_memory_history(memory_id):
    try:
        return memory.history(memory_id)
    except Exception as e:
        return jsonify({"message": str(e)}), 400


app.register_blueprint(api)
