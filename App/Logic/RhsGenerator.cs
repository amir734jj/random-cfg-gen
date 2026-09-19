using App.Models;

namespace App.Logic;

public class RhsGenerator
{
    private readonly RandomGen _randomGen;
    private readonly State _state;
    private readonly ItemGenerator _itemGenerator;
    private readonly Options _options;

    public RhsGenerator(RandomGen randomGen, State state, ItemGenerator itemGenerator, Options options)
    {
        _randomGen = randomGen;
        _state = state;
        _itemGenerator = itemGenerator;
        _options = options;
    }

    public string Invoke(string nt)
    {
        var epsilonAllowed = !_options.DisallowEpsilon && !_state.EpsilonGenerated[nt];
        var rhsCount = 0;
        if (!epsilonAllowed || !_randomGen.Chance(_options.EpsilonPercent))
        {
            rhsCount = 1 + _randomGen.RandomCount(_options.RhsContinuationPercent);
        }

        if (rhsCount == 0)
        {
            _state.EpsilonGenerated[nt] = true;
        }

        return string.Join(" ", Enumerable.Range(0, rhsCount)
            .Select(x => _itemGenerator.Invoke()));
    }
}