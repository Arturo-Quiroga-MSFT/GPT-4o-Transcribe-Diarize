using System;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        // Load environment variables from .env file
        LoadEnvFile("../.env");
        
        // Get Azure OpenAI configuration from environment variables
        string azureEndpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT");
        string apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY");
        string apiVersion = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_VERSION");
        string deploymentName = Environment.GetEnvironmentVariable("MODEL_DEPLOYMENT_NAME") ?? "gpt-4o-transcribe-diarize";
        
        // Validate required environment variables
        if (string.IsNullOrEmpty(azureEndpoint) || string.IsNullOrEmpty(apiKey) || string.IsNullOrEmpty(apiVersion))
        {
            Console.WriteLine("ERROR: Missing required environment variables.");
            Console.WriteLine("Please ensure .env file contains:");
            Console.WriteLine("  - AZURE_OPENAI_ENDPOINT");
            Console.WriteLine("  - AZURE_OPENAI_API_KEY");
            Console.WriteLine("  - AZURE_OPENAI_API_VERSION");
            return;
        }
        
        // Build Azure OpenAI endpoint URL
        string endpoint = $"{azureEndpoint.TrimEnd('/')}/openai/deployments/{deploymentName}/audio/transcriptions?api-version={apiVersion}";
        
        // Path to the audio file (update this to your test audio file)
        string audioFilePath = "../test_audio/teresa_5min.mp3";
        
        if (!File.Exists(audioFilePath))
        {
            Console.WriteLine($"ERROR: Audio file not found: {audioFilePath}");
            return;
        }
        
        Console.WriteLine("============================================================");
        Console.WriteLine("Azure OpenAI Transcription Test (.NET)");
        Console.WriteLine("============================================================");
        Console.WriteLine($"Endpoint: {azureEndpoint}");
        Console.WriteLine($"API Version: {apiVersion}");
        Console.WriteLine($"Deployment: {deploymentName}");
        Console.WriteLine($"Audio File: {audioFilePath}");
        Console.WriteLine("============================================================\n");
        
        using (var httpClient = new HttpClient())
        {
            // Azure OpenAI uses api-key header instead of Bearer token
            httpClient.DefaultRequestHeaders.Add("api-key", apiKey);
            
            using (var content = new MultipartFormDataContent())
            {
                // Add required fields
                content.Add(new StringContent(deploymentName), "model");
                content.Add(new StringContent("en"), "language");
                content.Add(new StringContent("0.0"), "temperature");
                content.Add(new StringContent("json"), "response_format");
                
                // Add chunking_strategy (REQUIRED for diarization models - must be 'server_vad')
                content.Add(new StringContent("{\"type\":\"server_vad\"}"), "chunking_strategy");
                
                // Add optional parameters
                content.Add(new StringContent("[\"word\",\"segment\"]"), "timestamp_granularities");
                content.Add(new StringContent("[\"logprobs\"]"), "include");
                
                // Add audio file
                var fileStream = File.OpenRead(audioFilePath);
                var fileContent = new StreamContent(fileStream);
                fileContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("audio/mpeg");
                content.Add(fileContent, "file", Path.GetFileName(audioFilePath));
                
                Console.WriteLine("Sending request to Azure OpenAI...\n");
                
                try
                {
                    HttpResponseMessage response = await httpClient.PostAsync(endpoint, content);
                    string result = await response.Content.ReadAsStringAsync();
                    
                    Console.WriteLine($"Status Code: {(int)response.StatusCode} {response.StatusCode}");
                    Console.WriteLine("\nRAW API RESPONSE:");
                    Console.WriteLine(result);
                    Console.WriteLine("\n============================================================");
                    
                    if (response.IsSuccessStatusCode)
                    {
                        Console.WriteLine("✓ Transcription completed successfully");
                        
                        // Check if response contains speaker segments
                        if (result.Contains("\"segments\"") || result.Contains("\"speaker\""))
                        {
                            Console.WriteLine("✓ Response contains speaker diarization data!");
                        }
                        else
                        {
                            Console.WriteLine("✗ WARNING: No speaker segments found in response");
                            Console.WriteLine("✗ Expected 'segments' field with speaker labels is missing");
                        }
                    }
                    else
                    {
                        Console.WriteLine("✗ Request failed");
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"✗ Error: {ex.Message}");
                    Console.WriteLine($"Stack Trace: {ex.StackTrace}");
                }
            }
        }
    }
    
    static void LoadEnvFile(string filePath)
    {
        if (!File.Exists(filePath))
        {
            Console.WriteLine($"WARNING: .env file not found at {filePath}");
            return;
        }
        
        foreach (var line in File.ReadAllLines(filePath))
        {
            var trimmedLine = line.Trim();
            if (string.IsNullOrWhiteSpace(trimmedLine) || trimmedLine.StartsWith("#"))
                continue;
                
            var parts = trimmedLine.Split('=', 2);
            if (parts.Length == 2)
            {
                Environment.SetEnvironmentVariable(parts[0].Trim(), parts[1].Trim());
            }
        }
    }
}