using System.Text.Json;

namespace App.Logic;

public class RandomGen
{
    private readonly Random _rnd = new Random();
    
    public TKey Rand<TKey>(IDictionary<TKey, double> dict) where TKey : notnull
    {
        var rndValue = _rnd.NextDouble() * dict.Sum(x => x.Value);
        var acc = 0.0;
        foreach (var (key, value) in dict.OrderBy(x => x.Value))
        {
            acc += value;
            if (rndValue <= acc)
            {
                return key;
            }
        }

        throw new Exception($"something is wrong with dictionary {JsonSerializer.Serialize(dict)}");
    }
}