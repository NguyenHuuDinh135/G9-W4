"""
Mangum wrapper for GeekBrain Monitoring API.
Allows FastAPI to run on AWS Lambda behind API Gateway.
"""

from mangum import Mangum
from monitoring_api import app

handler = Mangum(app, lifespan="off")
