from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *


BOOTSTRAP_SERVERS='localhost:9092'

if __name__ == "__main__":
   spark = SparkSession.builder.getOrCreate()

  
   schema = spark.read.option("multiLine", True).json('s3a://weatherdatastreaming/artifacts/weather_data.json').schema

 # I have to connect to the bootstrap servers, instead of kafka:9092
   df = spark \
       .readStream \
       .format("kafka") \
       .option("kafka.bootstrap.servers", BOOTSTRAP_SERVERS) \
       .option("subscribe", "dbserver1.DataStreaming.weatherdata") \
       .option("startingOffsets", "latest") \
       .load()

   transform_df = df.select(col("value").cast("string")).alias("value").withColumn("jsonData",from_json(col("value"),schema)).select("jsonData.payload.after.*")

   # S3 is a reliable location for the cluster and checkpoints
   checkpoint_location = "s3a://weatherdatastreaming/checkpoints"

   table_name = 'weatherdata'
   hudi_options = {
       'hoodie.table.name': table_name,
       "hoodie.datasource.write.table.type": "COPY_ON_WRITE",
       'hoodie.datasource.write.recordkey.field': 'id',
       'hoodie.datasource.write.partitionpath.field': '',
       'hoodie.datasource.write.table.name': table_name,
       'hoodie.datasource.write.operation': 'upsert',
       'hoodie.datasource.write.precombine.field': 'event_time',
      'hoodie.upsert.shuffle.parallelism': 100,
       'hoodie.insert.shuffle.parallelism': 100
   }

   s3_path = "s3a://weatherdatastreaming/output"


   def write_batch(batch_df, batch_id):
       batch_df.write.format("org.apache.hudi") \
       .options(**hudi_options) \
       .mode("append") \
       .save(s3_path)


   transform_df.writeStream.option("checkpointLocation", checkpoint_location).queryName("weather-streaming").foreachBatch(write_batch).start().awaitTermination()
