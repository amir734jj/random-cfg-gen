using App.Interfaces;
using App.Models;

namespace App.Logic;

public class ItemGenerator : IRandomTask<string>
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
        switch (_randomGen.Rand(_state.itemDistribution))
        {
            case ItemType.Terminal:
                return $@"""{_utilities.RandomLowerCaseString(_state.ItemLength)}""";
            case ItemType.NonTerminals:
                return _utilities.RandomNonTerminal(_state.NonTerminals);
            default:
                throw new ArgumentOutOfRangeException();
        }
    }
}