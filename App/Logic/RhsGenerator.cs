using App.Interfaces;
using App.Models;

namespace App.Logic;

public class RhsGenerator : IRandomTask<string>
{
    private readonly RandomGen _randomGen;
    private readonly State _state;
    private readonly ItemGenerator _itemGenerator;

    public RhsGenerator(RandomGen randomGen, State state, ItemGenerator itemGenerator)
    {
        _randomGen = randomGen;
        _state = state;
        _itemGenerator = itemGenerator;
    }
    
    public string Invoke()
    {
        return string.Join(" ", Enumerable.Range(0, _randomGen.Rand(_state.rhsDistribution))
            .Select(x => _itemGenerator.Invoke()));
    }
}