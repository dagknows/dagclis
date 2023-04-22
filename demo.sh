

DAG_TITLE="Dag4Demo"
NODE_PREFIX="$DAG_TITLE Node"

for dagid in `dk dags get | jq -r ".dags| .[] | select(.title|test(\"^$DAG_PREFIX\")) | .id"`; do
  echo "Deleting Dag $dagid"
  dk dags delete $dagid
done

# Also remove test nodes
for nodeid in `dk nodes get | jq -r ".nodes | .[] | .node | select(.title|test(\"^$NODE_PREFIX\")) | .id"`; do
  echo "Deleting node $nodeid"
  dk nodes delete $nodeid
done

dk dags create --title "$DAG_TITLE"
CURR_DAG_ID=`dk dags get | jq -r ".dags | .[] | select(.title == \"$DAG_TITLE\") | .id"`

echo "Creating 10 demo nodes"
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

NODEID1=`dk nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 1\") | .id"`
NODEID2=`dk nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 2\") | .id"`
NODEID3=`dk nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 3\") | .id"`
NODEID4=`dk nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 4\") | .id"`
NODEID5=`dk nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 5\") | .id"`
NODEID6=`dk nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 6\") | .id"`
NODEID7=`dk nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 7\") | .id"`
NODEID8=`dk nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 8\") | .id"`
NODEID9=`dk nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 9\") | .id"`
NODEID10=`dk nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 10\") | .id"`

echo "Creating edges"
dk dag connect --dag-id $CURR_DAG_ID --src-node-id $NODEID1 --dest-node-id $NODEID2
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID1 --dest-node-id $NODEID2
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID1 --dest-node-id $NODEID3
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID2 --dest-node-id $NODEID4
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID2 --dest-node-id $NODEID5
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID3 --dest-node-id $NODEID6
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID3 --dest-node-id $NODEID7
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID4 --dest-node-id $NODEID8
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID5 --dest-node-id $NODEID8
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID6 --dest-node-id $NODEID9
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID7 --dest-node-id $NODEID9
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID8 --dest-node-id $NODEID10
dk dags connect --dag-id $CURR_DAG_ID --src-node-id $NODEID9 --dest-node-id $NODEID10
