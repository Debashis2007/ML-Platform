FROM public.ecr.aws/lambda/python:3.11

COPY export_governance.py ${LAMBDA_TASK_ROOT}/

CMD ["export_governance.handler"]
