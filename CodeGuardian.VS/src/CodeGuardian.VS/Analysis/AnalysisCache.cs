using System;
using System.Collections.Generic;

namespace CodeGuardian.VS.Analysis
{
    /// <summary>
    /// Cache thread-safe de resultados de análise com expiração automática de 30 segundos.
    /// </summary>
    public sealed class AnalysisCache
    {
        private readonly object _lock = new object();
        private readonly Dictionary<string, CacheEntry> _entries = new Dictionary<string, CacheEntry>(StringComparer.OrdinalIgnoreCase);
        private readonly TimeSpan _ttl;

        public AnalysisCache(TimeSpan? ttl = null)
        {
            _ttl = ttl ?? TimeSpan.FromSeconds(30);
        }

        /// <summary>
        /// Retorna resultado em cache se ainda válido, ou null se expirado/inexistente.
        /// </summary>
        public GuardianResult? GetOrNull(string filePath)
        {
            lock (_lock)
            {
                if (!_entries.TryGetValue(filePath, out var entry))
                    return null;

                if (DateTime.UtcNow - entry.CachedAt > _ttl)
                {
                    _entries.Remove(filePath);
                    return null;
                }

                return entry.Result;
            }
        }

        /// <summary>
        /// Armazena ou atualiza resultado no cache.
        /// </summary>
        public void Set(string filePath, GuardianResult result)
        {
            lock (_lock)
            {
                _entries[filePath] = new CacheEntry(result, DateTime.UtcNow);
            }
        }

        /// <summary>
        /// Remove entrada do cache — chamado quando o arquivo é salvo.
        /// </summary>
        public void Invalidate(string filePath)
        {
            lock (_lock)
            {
                _entries.Remove(filePath);
            }
        }

        /// <summary>
        /// Remove todas as entradas do cache.
        /// </summary>
        public void Clear()
        {
            lock (_lock)
            {
                _entries.Clear();
            }
        }

        private readonly struct CacheEntry
        {
            public GuardianResult Result { get; }
            public DateTime CachedAt { get; }

            public CacheEntry(GuardianResult result, DateTime cachedAt)
            {
                Result = result;
                CachedAt = cachedAt;
            }
        }
    }
}
