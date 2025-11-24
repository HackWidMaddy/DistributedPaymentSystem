import java.io.IOException;
import java.util.StringTokenizer;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

public class MaxJobStatus {

    // Mapper Class
    public static class StatusMapper extends Mapper<Object, Text, Text, IntWritable> {

        private final static IntWritable one = new IntWritable(1);
        private Text word = new Text();
        private boolean isHeader = true; // Flag to skip header

        public void map(Object key, Text value, Context context) throws IOException, InterruptedException {
            // Skip the header line
            if (isHeader) {
                isHeader = false;
                return;
            }

            String line = value.toString();
            String[] fields = line.split(","); // Assuming CSV, split by comma

            if (fields.length >= 5) { // Ensure 'status' field exists (5th column, index 4)
                String status = fields[4].trim(); // Get the status and trim whitespace
                if (!status.isEmpty()) { // Only emit if status is not empty
                    word.set(status);
                    context.write(word, one);
                }
            }
        }
    }

    // Reducer Class
    public static class IntSumReducer extends Reducer<Text, IntWritable, Text, IntWritable> {
        private IntWritable result = new IntWritable();

        public void reduce(Text key, Iterable<IntWritable> values, Context context)
                throws IOException, InterruptedException {
            int sum = 0;
            for (IntWritable val : values) {
                sum += val.get();
            }
            result.set(sum);
            context.write(key, result);
        }
    }

    // Main Driver
    public static void main(String[] args) throws Exception {
        Configuration conf = new Configuration();
        Job job = Job.getInstance(conf, "video job status count");
        
        job.setJarByClass(MaxJobStatus.class); // Specify the main class
        job.setMapperClass(StatusMapper.class); // Specify the Mapper class
        job.setCombinerClass(IntSumReducer.class); // Optional: Use Reducer as Combiner for optimization
        job.setReducerClass(IntSumReducer.class); // Specify the Reducer class
        
        // Specify output key and value types for Mapper
        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(IntWritable.class);

        // Specify output key and value types for Reducer (final output)
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(IntWritable.class);

        // Set input and output paths from command line arguments
        FileInputFormat.addInputPath(job, new Path(args[0]));
        FileOutputFormat.setOutputPath(job, new Path(args[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1); // Run the job and exit
    }
}