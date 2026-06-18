# Remote state: partial backend (values supplied at init via -backend-config).
# See environments/*.backend.hcl.example and environments/README.md.
terraform {
  backend "s3" {}
}