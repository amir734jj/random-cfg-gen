using App.Logic;
using App.Models;
using CommandLine;
using Microsoft.Extensions.DependencyInjection;

namespace App;

class Program
{
    public static void Main(string[] args)
    {
        var result = Parser.Default.ParseArguments<Options>(args);

        if (result.Errors.Any())
        {
            return;
        }

        if (result.Value.RhsContinuationPercent is < 0 or > 99
            || result.Value.AlternativeContinuationPercent is < 0 or > 99
            || result.Value.EpsilonPercent is < 0 or > 100)
        {
            Console.Error.WriteLine(
                "continuation percentages must be between 0 and 99; epsilon percent must be between 0 and 100");
            Environment.ExitCode = 1;
            return;
        }
        
        var serviceCollection = new ServiceCollection();
        serviceCollection.Scan(opt =>
        {
            opt.FromCallingAssembly()
                .AddClasses()
                .AsSelf();
        });

        serviceCollection.AddSingleton(
            result.Value.Seed is int seed ? new Random(seed) : new Random());
        serviceCollection.AddSingleton(result.Value);
        serviceCollection.AddSingleton<State>(x =>
        {
            var state = new State(x.GetRequiredService<Utilities>());
            state.Initialize(result.Value);
            return state;
        });
        
        var serviceProvider = serviceCollection
            .BuildServiceProvider();

        var cfg = serviceProvider.GetRequiredService<CfgGenerator>().Invoke();
        
        Console.WriteLine(cfg);
    }
}