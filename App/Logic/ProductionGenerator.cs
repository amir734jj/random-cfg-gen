using App.Interfaces;
using App.Logic;
using App.Models;

namespace App;

public class ProductionGenerator : IRandomTask<List<string>>
{
    private readonly RandomGen _randomGen;
    private readonly State _state;
    private readonly RhsGenerator _rhsGenerator;

    public ProductionGenerator(RandomGen randomGen, State state, RhsGenerator rhsGenerator)
    {
        _randomGen = randomGen;
        _state = state;
        _rhsGenerator = rhsGenerator;
    }
    
    public List<string> Invoke()
    {
        return Enumerable.Range(0, _randomGen.Rand(_state.productionsDistribution))
            .Select(x => _rhsGenerator.Invoke())
            .ToList();
    }
}