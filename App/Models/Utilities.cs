namespace App.Models;

public class Utilities
{
    private readonly Random _random;

    public Utilities(Random random)
    {
        _random = random;
    }
    
    public string RandomLowerCaseString(int length)
    {
        const string chars = "abcdefghijklmnopqrstuvwxyz";
        return new string(Enumerable.Repeat(chars, length)
            .Select(s => s[_random.Next(s.Length)]).ToArray());
    }

    public string RandomUpperCaseString(int length)
    {
        const string chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        return new string(Enumerable.Repeat(chars, length)
            .Select(s => s[_random.Next(s.Length)]).ToArray());
    }

    public string RandomNonTerminal(List<string> nonTerminals)
    {
        return nonTerminals[_random.Next(nonTerminals.Count)];
    }
}