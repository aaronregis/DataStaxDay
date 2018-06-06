**[Back to Agenda](./../README.md)**


Use the following IPs:  

Group 1 => Cluster 1

Group 2 => Cluster 2

Group 3 => Cluster 3

etc.

|  Group          | Node0          |  Node1         | Node2           | OpsCenter
|-----------------|----------------|----------------|-----------------|----------------
| Cluster 1       | 40.114.26.3    | 40.121.44.43   | 40.121.62.128   | 40.121.34.96
| Cluster 2       | 137.135.126.26 | 137.135.120.72 | 137.135.121.231 | 137.135.122.63
| Cluster 3       | 137.135.118.78 | 137.135.114.228| 137.117.42.168  | 137.135.126.86
| Cluster 4       | 138.91.123.253 | 104.41.135.159 | 138.91.125.37   | 138.91.124.113
| Cluster 5       | 137.117.85.20  | 138.91.125.250 | 137.117.87.168  | 137.117.80.134

e.g.

For Cluster 1,

OpsCenter login page
http://40.121.34.96:8888

Solr admin page
http://40.114.26.3:8983/solr

Spark admin page
http://40.114.26.3:7080

**[Back to Agenda](./../README.md)**

insert:
  partitions: fixed(10)
  batchtype: UNLOGGED 
