using System;
using CodeGuardian.VS.Analysis;
using Microsoft.VisualStudio.Shell.Interop;
using Microsoft.VisualStudio.Shell.TableControl;
using Microsoft.VisualStudio.Shell.TableManager;

namespace CodeGuardian.VS.ErrorList
{
    /// <summary>
    /// Representa uma linha da Error List do Visual Studio para um issue do Code Guardian.
    /// Implementa ITableEntry conforme API moderna (VS 2019/2022 — não usa o legado IVsTaskList).
    /// </summary>
    public sealed class GuardianTableEntry : ITableEntry
    {
        private readonly IssueResult _issue;

        public GuardianTableEntry(IssueResult issue)
        {
            _issue = issue;
        }

        public bool TryGetValue(string keyName, out object? content)
        {
            content = keyName switch
            {
                StandardTableKeyNames.ErrorSeverity => MapearSeveridade(_issue.Severity),
                StandardTableKeyNames.Text => _issue.Message,
                StandardTableKeyNames.DocumentName => _issue.File,
                StandardTableKeyNames.Line => Math.Max(0, _issue.Line - 1),  // Error List usa 0-indexed
                StandardTableKeyNames.Column => 0,
                StandardTableKeyNames.ErrorCode => _issue.RuleId,
                StandardTableKeyNames.ErrorSource => "Code Guardian",
                StandardTableKeyNames.BuildTool => "Code Guardian",
                StandardTableKeyNames.ErrorCategory => _issue.Category,
                _ => null,
            };

            return content != null;
        }

        public bool CanSetValue(string keyName) => false;

        public bool TrySetValue(string keyName, object content) => false;

        /// <summary>
        /// Mapeia severity do Code Guardian para __VSERRORCATEGORY do Visual Studio.
        /// </summary>
        private static __VSERRORCATEGORY MapearSeveridade(string severity) =>
            severity?.ToLowerInvariant() switch
            {
                "critical" => __VSERRORCATEGORY.EC_ERROR,
                "error" => __VSERRORCATEGORY.EC_ERROR,
                "warning" => __VSERRORCATEGORY.EC_WARNING,
                "info" => __VSERRORCATEGORY.EC_MESSAGE,
                _ => __VSERRORCATEGORY.EC_WARNING,
            };

        public object Identity => $"{_issue.File}:{_issue.Line}:{_issue.RuleId}";
    }
}
