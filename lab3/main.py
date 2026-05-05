from fastapi import FastAPI
import subprocess
import json
import uuid

app = FastAPI()

MINIO_ALIAS = "myminio"

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

@app.post("/storage/create")
def create_storage(user_id: str):
    access = f"user{user_id}"
    secret = str(uuid.uuid4())

    bucket = f"user-{user_id}"

    run(f"mc admin user add {MINIO_ALIAS} {access} {secret}")

    run(f"mc mb {MINIO_ALIAS}/{bucket}")

    policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
          "Effect": "Allow",
          "Action": ["s3:*"],
          "Resource": [
              f"arn:aws:s3:::{bucket}",
              f"arn:aws:s3:::{bucket}/*"
          ]
        }
      ]
    }

    with open("policy.json", "w") as f:
        json.dump(policy, f, indent=2)

    run(f"mc admin policy add {MINIO_ALIAS} {access}-policy policy.json")
    run(f"mc admin policy set {MINIO_ALIAS} {access}-policy user={access}")

    return {
        "endpoint": "http://localhost:9000",
        "access_key": access,
        "secret_key": secret,
        "bucket": bucket
    }


@app.delete("/storage/{user_id}")
def delete_storage(user_id: str):
    access = f"user{user_id}"
    bucket = f"user-{user_id}"

    run(f"mc rb --force {MINIO_ALIAS}/{bucket}")
    run(f"mc admin user remove {MINIO_ALIAS} {access}")

    return {"status": "deleted"}