using App.Models;

namespace App.Logic;

public class ItemGenerator
{
    private readonly RandomGen _randomGen;
    private readonly State _state;
    private readonly Utilities _utilities;

    public ItemGenerator(RandomGen randomGen, State state, Utilities utilities)
    {
        _randomGen = randomGen;
        _state = state;
        _utilities = utilities;
    }
    
    public string Invoke()
    {
        return _randomGen.Rand(_state.itemDistribution) switch
        {
            ItemType.Terminal => $@"""{_utilities.RandomLowerCaseString(_state.ItemLength)}""",
            ItemType.NonTerminals => _utilities.RandomNonTerminal(_state.NonTerminals),
            _ => throw new ArgumentOutOfRangeException()
        };
    }
}