# Weather Check Streaming Pipeline
## Project Objective
The project is to develop a comprehensive data processing system that captures and processes real-time weather data for analysis. The system will harness the OpenWeather API to collect data, which will then be routed through Apache NiFi for preprocessing. The processed data will be stored in a MySQL database, with Debezium tracking changes for real-time capture. Apache Kafka will be used to handle the data stream, allowing Apache Spark Streaming to process the data for updates and analytical computations. Apache Hudi will manage the efficient storage and retrieval of this data on AWS S3, ensuring data consistency and accessibility with cost-efftective benefit. Finally, Amazon Athena will be utilized to query the data, facilitating complex analytical tasks, with the results visualized for data-driven decision-making and reporting.

![data streaming](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/b53e2ac0-08fe-4ad0-badc-df88f201087f)

## Detailed Steps

### a.Apache Nifi
I use Apache NiFi to extract data from the OpenWeather API and send it to the MySQL database to make data available for further consumption. Apache NiFi is a highly scalable, drag-and-drop data engineering tool that can be considered as a Swiss Army knife for big data integration. It can consume and send data bidirectionally in batches or streams to numerous data sources. To deploy NiFi, debezium and mysql I use Docker running on EC2 instance.
![Screenshot 2024-03-03 192057](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/5d344cf8-7905-4d15-aa80-dbec6412b3b8)

In the Mysql Database, I created the table for the future data dump. The auto_increment id was creaded as Primary Key and datetime column was created for building Slow Changeing Dimension in the future.
![Mysql](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/b1e8b45d-effe-45c4-8753-e8d347005d07)

In the Nif, I used InvokeHTTP Processor to extract the real-time data from Backend API(OpenWeather), since the data is in Nest Json format, I deployed FlattenJson Processor to flat the file. QueryRecord Processor is used to put the query for the data from the FlowFile. Finally, put the data into my MySQL Database.<br>

Whole Nifi Structure:<br>
![Screenshot 2024-03-03 183442](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/aa998985-2d25-4fa6-9c8f-d72ab7961f32)


InvokeHTTP Processor:<br>
![Screenshot 2024-03-03 193255](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/e9b53b0f-7e20-484b-a171-bd379def5f3f)


FlattenJson Processor:<br>
![Screenshot 2024-03-03 193342](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/d2fdca83-b4b8-40bf-8791-1f0e0c328ebb)

QueryRecord Processor:<br>
![Screenshot 2024-03-03 193743](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/7a93ee7d-871a-4a10-9466-55237e86f13c)

PutDatabaseRecord Processor:<br>
![Screenshot 2024-03-03 193901](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/2153c1bd-0948-47b2-93bc-8391739853d7)

Output of Nifi:<br>
![Screenshot 2024-03-03 194153](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/f2f28ec5-8eac-4892-ae47-ce5a7a1ea9b8)

MySQL Database:<br>
![Screenshot 2024-03-03 194402](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/2de01476-fdea-4216-9fb6-cf742cd17c41)

### b.Debezium and Kafka
Running Debezium involves Zookeeper, Kafka, and services that run Debezium's connectors. Debezium is a distributed platform that turns my existing databases into event streams, so applications can quickly react to each row-level change in the databases. Debezium is built on top of Kafka and provides Kafka Connect compatible connectors that monitor specific database management systems. Debezium records the history of data changes in my Kafka topics.<br>

I was setting up Zookeeper<br>
```ruby
docker run -dit --name zookeeper -p 2181:2181 -p 2888:2888 -p 3888:3888 debezium/zookeeper:1.6
```
Created a Kafka Container<br>
```ruby
docker run -dit --name kafka -p 9092:9092 --link zookeeper:zookeeper debezium/kafka:1.6
```
Created a connection with Kafka, Zookeeper and MySQL Containers.<br>
```ruby
docker run -dit --name connect -p 8083:8083 -e GROUP_ID=1 -e CONFIG_STORAGE_TOPIC=my-connect-configs -e OFFSET_STORAGE_TOPIC=my-connect-offsets -e STATUS_STORAGE_TOPIC=my_connect_statuses --link zookeeper:zookeeper --link kafka:kafka --link mysql:mysql debezium/connect:1.6
```
enable MySQL debezium connector for Kafka Connect, so I can start monitoring changes in our MySQL target table.<br>
```ruby
curl -i -X POST -H "Accept:application/json" -H "Content-Type:application/json" localhost:8083/connectors/ -d '{ "name": "inventory-connector1", "config": { "connector.class": "io.debezium.connector.mysql.MySqlConnector", "tasks.max": "1", "database.hostname": "mysql", "database.port": "3306", "database.user": "debezium", "database.password": "dbz", "database.server.id": "184054", "database.server.name": "dbserver1", "database.include.list": "DataStreaming", "database.history.kafka.bootstrap.servers": "kafka:9092", "database.history.kafka.topic": "dbhistory.DataStreaming" } }'
```
Then I can check if my Kafka is receiving the data<br>
```ruby
bin/kafka-console-consumer.sh --topic dbserver1.DataStreaming.weatherdata --bootstrap-server 88100c4d3c93:9092
```
My Kafka is recieving the data.<br>
![Screenshot 2024-03-03 195833](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/c5f7344c-4ce6-4a55-bf46-2f52777b4077)

A Json file was created to infrer Schema for my Spark Streaming later.

### c.Spark and Hudi
1). A python script was created to read a stream of data from Kafka, transform it, and then write the processed data to Apache Hudi, which in turn stores it on AWS S3.<br>

2). use Spark-submit for submitting the spark streaming app.<br>
```ruby
./spark-submit --master local[*] --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.3,org.apache.hudi:hudi-spark3-bundle_2.12:0.12.3 --conf "spark.serializer=org.apache.spark.serializer.KryoSerializer" /home/ec2-user/new/pyspark_streaming.py
```
### d.AWS Athena and S3
Use Athena to connect S3 and get I can get the run the query to get the Real-Time weather data which BI team can use the data to build Weather Analysis Tool.
![Screenshot 2024-03-03 201015](https://github.com/LeoMeng5223655/Streaming-Pipeline-Project/assets/131537129/398e72ab-a8be-4103-994f-bee963a7e9d3)


















