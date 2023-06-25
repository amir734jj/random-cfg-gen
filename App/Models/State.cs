namespace App.Models;

public class State
{
    private readonly Utilities _utilities;
    
    public List<string> NonTerminals { get; set; }

    public Dictionary<string, bool> EpsilonGenerated = new();

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
        var generatedNonTerminals = new HashSet<string>();
        
        // Avoid duplicate non-terminal
        foreach (var _ in Enumerable.Range(0, options.NonTerminals))
        {
            var addedNonTerminal = false;
            var itemSize = options.ItemLength;
            
            do
            {
                var nt = _utilities.RandomUpperCaseString(itemSize);

                if (!generatedNonTerminals.Contains(nt))
                {
                    generatedNonTerminals.Add(nt);
                    addedNonTerminal = true;
                }
                else
                {
                    itemSize++;
                }
            } while (!addedNonTerminal);
        }

        NonTerminals = generatedNonTerminals.ToList();

        EpsilonGenerated = NonTerminals.ToDictionary(x => x, _ => false);

        this.ItemLength = options.ItemLength;
    }
}