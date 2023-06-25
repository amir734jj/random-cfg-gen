namespace App.Models;

public class State
{
    private readonly Utilities _utilities;
    public List<string> NonTerminals { get; set; }

    /// <summary>
    /// Number of characters in each item
    /// </summary>
    public int ItemLength = 5;

    public IDictionary<ItemType, double> itemDistribution = new Dictionary<ItemType, double>
    {
        { ItemType.Terminal, 3 },
        { ItemType.NonTerminals, 2 },
    };
    
    public IDictionary<int, double> rhsDistribution = new Dictionary<int, double>
    {
        { 0, 4 },
        { 10, 3 },
        { 15, 2 },
        { 20, 1 }
    };
    
    public IDictionary<int, double> productionsDistribution = new Dictionary<int, double>
    {
        { 2, 5 },
        { 4, 3 },
        { 8, 2 },
        { 16, 1 },
    };

    public State(Utilities utilities)
    {
        _utilities = utilities;
    }

    public void Initialize(Options options)
    {
        NonTerminals = Enumerable.Range(0, options.NonTerminals)
            .Select(_ => _utilities.RandomUpperCaseString(this.ItemLength))
            .ToList();

        this.ItemLength = options.ItemLength;
    }
}