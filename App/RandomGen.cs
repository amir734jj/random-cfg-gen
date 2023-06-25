namespace App;

public class RandomGen
{
    private readonly Random _rnd = new Random();
    
    public TKey Rand<TKey>(Dictionary<TKey, double> dict) where TKey : notnull
    {
        foreach (var (key, value) in dict.OrderByDescending(x => x.Value))
        {
            if (value >= _rnd.NextDouble())
            {
                return key;
            }
        }

        throw new Exception("something is wrong");
    }
}