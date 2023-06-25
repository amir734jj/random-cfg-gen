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
        
        var serviceCollection = new ServiceCollection();
        serviceCollection.Scan(opt =>
        {
            opt.FromCallingAssembly()
                .AddClasses()
                .AsSelf();
        });

        serviceCollection.AddSingleton(new Random());
        serviceCollection.AddSingleton<State>((x) =>
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