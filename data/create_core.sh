#Simple script to create solr cores and reload/index with the right XML's
if [ $# -eq 0 ]
  then
    echo "No arguments supplied"
    echo "./create_core.sh <name of your keyspace>"
    exit 1
fi

#add the path to dsetool if dsetool is not in your path
echo 'Creating Solr cores...'
dsetool -l cassandra -p Password1234 create_core $1.metadata schema=schema_metadata.xml solrconfig=solr_config_metadata.xml reindex=true
dsetool -l cassandra -p Password1234 create_core $1.rank schema=schema_rank.xml solrconfig=solr_config_rank.xml reindex=true
dsetool -l cassandra -p Password1234 create_core $1.clicks schema=schema_clicks.xml solrconfig=solr_config_clicks.xml reindex=true
echo 'finished creating Solr cores!'
