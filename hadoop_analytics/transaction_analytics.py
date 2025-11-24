from mrjob.job import MRJob
from mrjob.step import MRStep

class TransactionAnalytics(MRJob):

    def steps(self):
        return [
            MRStep(mapper=self.mapper_get_amounts,
                   reducer=self.reducer_sum_amounts),
            MRStep(reducer=self.reducer_find_top_merchant)
        ]

    def mapper_get_amounts(self, _, line):
        # Line format: transaction_id,sender,receiver,amount,timestamp
        try:
            parts = line.split(',')
            receiver = parts[2]
            amount = float(parts[3])
            yield receiver, amount
        except:
            pass

    def reducer_sum_amounts(self, receiver, amounts):
        yield None, (sum(amounts), receiver)

    def reducer_find_top_merchant(self, _, merchant_counts):
        # Find the merchant with the highest total transaction volume
        yield max(merchant_counts)

if __name__ == '__main__':
    TransactionAnalytics.run()
