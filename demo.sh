$!/bin/sh

dk dags get
DAG_TITLE="Dag For Demo 4"
dk dags create --title "$DAG_TITLE"
CURR_DAG_ID=`dk dags get | jq -r ".dags | .[] | select(.title == \"$DAG_TITLE\") | .id"`
dk dags get $CURR_DAG_ID

NODE_PREFIX="$DAG_TITLE Node"
dk nodes create --title "$NODE_PREFIX 1" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 2" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 3" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 4" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 5" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 6" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 7" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 8" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 9" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 10" --dag-id $CURR_DAG_ID
