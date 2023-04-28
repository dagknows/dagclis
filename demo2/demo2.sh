
dk dags create --title "Server Health Check"
dk nodes create --title "CPU Health Check"
dk nodes modify HeoYZsAds9h2kOwBovMYfvoeh1PN49x0 --detection-script demo2/cpu_health_check.py
dk dags add-nodes --dag-id wQMIx6VrRAD7qIuPoKl5CGXom7rYjOr2 --node-ids HeoYZsAds9h2kOwBovMYfvoeh1PN49x0
dk nodes modify HeoYZsAds9h2kOwBovMYfvoeh1PN49x0 --input-params hostname
dk execs new --dag-id wQMIx6VrRAD7qIuPoKl5CGXom7rYjOr2 --node-id HeoYZsAds9h2kOwBovMYfvoeh1PN49x0  --proxy ourproxy --session-id l7vw5pVsMS7YmHi3RxnT5Q --file demo2/params.json
dk execs get eMOKubILdUovpqW8
