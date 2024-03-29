
SESSION_SUBJECT="Session4DemoSri"
DAG_TITLE="Dag4DemoSri"
NODE_PREFIX="$DAG_TITLE Node"

for sessionid in `dk --format=json sessions get | jq -r ".sessions| .[] | select(.subject != null) | select(.subject|test(\"^$SESSION_SUBJECT\")) | .id"`; do
  echo "Deleting Demo Session $sessionid"
  dk sessions delete $sessionid
done

for dagid in `dk --format=json dags get | jq -r ".dags| .[] | select(.title != null) | select(.title|test(\"^$DAG_TITLE\")) | .id"`; do
  echo "Deleting Demo Dag $dagid"
  dk dags delete $dagid
done

# Also remove test nodes
for nodeid in `dk --format=json  nodes get | jq -r ".nodes | .[] | .node | select(.title != null) | select(.title|test(\"^$NODE_PREFIX\")) | .id"`; do
  echo "Deleting Demo Node $nodeid"
  dk nodes delete $nodeid
done

dk sessions create --subject "$SESSION_SUBJECT"

dk dags create --title "$DAG_TITLE"
CURR_DAG_ID=`dk --format=json dags get | jq -r ".dags | .[] | select(.title != null) | select(.title == \"$DAG_TITLE\") | .id"`
CURR_SESSION_ID=`dk --format=json sessions get | jq -r ".sessions| .[] | select(.subject != null) | select(.subject|test(\"^$SESSION_SUBJECT\")) | .id"`

echo "Creating 10 demo nodes"
dk nodes create --title "$NODE_PREFIX 1"
dk nodes create --title "$NODE_PREFIX 2"
dk nodes create --title "$NODE_PREFIX 3"
dk nodes create --title "$NODE_PREFIX 4"
dk nodes create --title "$NODE_PREFIX 5"
dk nodes create --title "$NODE_PREFIX 6" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 7" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 8" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 9" --dag-id $CURR_DAG_ID
dk nodes create --title "$NODE_PREFIX 10" --dag-id $CURR_DAG_ID

NODEID1=`dk --format=json nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 1\") | .id"`
NODEID2=`dk --format=json nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 2\") | .id"`
NODEID3=`dk --format=json nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 3\") | .id"`
NODEID4=`dk --format=json nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 4\") | .id"`
NODEID5=`dk --format=json nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 5\") | .id"`
NODEID6=`dk --format=json nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 6\") | .id"`
NODEID7=`dk --format=json nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 7\") | .id"`
NODEID8=`dk --format=json nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 8\") | .id"`
NODEID9=`dk --format=json nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 9\") | .id"`
NODEID10=`dk --format=json nodes get | jq -r ".nodes | .[] | .node | select(.title == \"$NODE_PREFIX 10\") | .id"`

# Bulk adding nodes to a dag
dk dags add-nodes --dag-id $CURR_DAG_ID --node-ids $NODEID1 $NODEID2 $NODEID3 $NODEID4 $NODEID5

echo "Creating edges"
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

echo name1 = \"$NODEID1 - $NODE_PREFIX 1\" ; print(name1) > /tmp/node1
echo name3 = \"$NODEID1 - $NODE_PREFIX 1\" ; print(name3) > /tmp/node3
echo name5 = \"$NODEID1 - $NODE_PREFIX 1\" ; print(name5) > /tmp/node5
echo name7 = \"$NODEID1 - $NODE_PREFIX 1\" ; print(name7) > /tmp/node7
echo name9 = \"$NODEID1 - $NODE_PREFIX 1\" ; print(name9) > /tmp/node9

dk nodes modify $NODEID1 --detection-script /tmp/node1
dk nodes modify $NODEID3 --detection-script /tmp/node3
dk nodes modify $NODEID5 --detection-script /tmp/node5
dk nodes modify $NODEID7 --detection-script /tmp/node7
dk nodes modify $NODEID9 --detection-script /tmp/node9

dk nodes modify $NODEID2 --detection "echo \"Executing $NODEID1 - $NODE_PREFIX 2\""
dk nodes modify $NODEID4 --detection "echo \"Executing $NODEID1 - $NODE_PREFIX 4\""
dk nodes modify $NODEID6 --detection "echo \"Executing $NODEID1 - $NODE_PREFIX 6\""
dk nodes modify $NODEID8 --detection "echo \"Executing $NODEID1 - $NODE_PREFIX 8\""
dk nodes modify $NODEID10 --detection "echo \"Executing $NODEID1 - $NODE_PREFIX 10\""

# Now create an execution
dk execs new --dag-id "$CURR_DAG_ID" --node-id "$NODEID1" --session-id "$CURR_SESSION_ID"  --proxy ourproxy
