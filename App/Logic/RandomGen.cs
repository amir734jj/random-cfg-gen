using System.Text.Json;

namespace App.Logic;

public class RandomGen
{
    private readonly Random _random;

    public RandomGen(Random random)
    {
        _random = random;
    }

    public int RandomCount(int continuationPercent)
    {
        var count = 0;
        while (_random.Next(100) < continuationPercent)
        {
            count++;
        }

        return count;
    }

    public bool Chance(int percent) => _random.Next(100) < percent;
    
    public TKey Rand<TKey>(IDictionary<TKey, double> dict) where TKey : notnull
    {
        var rndValue = _random.NextDouble() * dict.Sum(x => x.Value);
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