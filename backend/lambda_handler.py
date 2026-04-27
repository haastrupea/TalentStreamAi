"""AWS Lambda entrypoint — configure the function handler as ``lambda_handler.handler``."""

from mangum import Mangum

from app.main import app

handler = Mangum(app)
