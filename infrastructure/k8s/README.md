[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

This directory contains Kubernetes manifests for running background jobs.

`spot-gpu-cronjob.yaml` defines a CronJob that periodically dequeues work for
GPU spot instances. The worker container runs `evolution-worker:latest` with one
GPU request. Modify the schedule or image as needed for your cluster.
