import sys

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

console = Console()


def calculate_valuation(data):
    """
    Calculates the share valuation based on the provided data.
    """
    df = pd.DataFrame(data)

    # 1. Net Income per share
    df["NI_per_share"] = df["NetIncome"] / df["Shares"]

    # 2. Weighted average Net Income per share
    # Weights: Latest Year: 3, Year-1: 2, Year-2: 1
    df = df.sort_values("Year", ascending=False)
    latest_year = df["Year"].max()

    weights = {latest_year: 3, latest_year - 1: 2, latest_year - 2: 1}

    # Calculate weighted sum
    weighted_sum = (df["NI_per_share"] * df["Year"].map(weights)).sum()
    weighted_avg_NI = weighted_sum / 6

    # 3. Calculation values
    A = weighted_avg_NI * 10  # Profit Value (순손익가치)

    # Asset Value (순자산가치) - Using the latest year data
    latest_data = df[df["Year"] == latest_year].iloc[0]
    B = latest_data["Equity"] / latest_data["Shares"]

    C = (A * 3 + B * 2) / 5  # Weighted Average Value (가중평균가치)
    P = max(C, B * 0.8)  # Final Valuation per share (최종 1주당 평가액)

    total_shares = latest_data["Shares"]
    equity_value_3922 = P * total_shares * 0.3922

    return {
        "df": df,
        "weighted_avg_NI": weighted_avg_NI,
        "profit_value": A,
        "asset_value": B,
        "avg_value": C,
        "final_price": P,
        "total_shares": total_shares,
        "target_equity_value": equity_value_3922,
    }


def display_results(results):
    df = results["df"]

    # Input Data Table
    table = Table(
        title="\n[bold blue]1. 입력 데이터 및 1주당 순손익액 현황[/bold blue]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("연도", justify="center")
    table.add_column("발행주식수", justify="right")
    table.add_column("자기자본", justify="right")
    table.add_column("당기순이익", justify="right")
    table.add_column("1주당 순손익", justify="right", style="green")

    for _, row in df.iterrows():
        table.add_row(
            str(int(row["Year"])),
            f"{row['Shares']:,.0f}",
            f"{row['Equity']:,.0f}",
            f"{row['NetIncome']:,.0f}",
            f"{row['NI_per_share']:,.0f}",
        )

    console.print(table)

    # Valuation Summary
    summary = Table(
        title="\n[bold cyan]2. 기업가치 평가 상세 결과[/bold cyan]",
        show_header=False,
        box=None,
    )
    summary.add_column("구분", style="bold white")
    summary.add_column("계산 결과", justify="right")

    summary.add_row("가중평균 1주당 순손익액", f"{results['weighted_avg_NI']:,.0f} 원")
    summary.add_row(
        "순손익가치 (A = 순손익액 * 10)", f"{results['profit_value']:,.0f} 원"
    )
    summary.add_row(
        "순자산가치 (B = 자기자본 / 주식수)", f"{results['asset_value']:,.0f} 원"
    )
    summary.add_row(
        "가중평균가치 (C = (A*3 + B*2) / 5)", f"{results['avg_value']:,.0f} 원"
    )
    summary.add_row(
        "최종 1주당 평가액 (max(C, B*0.8))",
        f"[bold yellow]{results['final_price']:,.0f} 원[/bold yellow]",
    )
    summary.add_row("-" * 20, "-" * 20)
    summary.add_row("기준일 발행주식 총수", f"{results['total_shares']:,.0f} 주")
    summary.add_row(
        "39.22% 지분 가치 평가액",
        f"[bold green]{results['target_equity_value']:,.0f} 원[/bold green]",
    )

    console.print(
        Panel(summary, title="[산출 요약]", expand=False, border_style="bright_blue")
    )


def main():
    while True:
        console.clear()
        console.print(
            Panel.fit(
                "[bold white]비상장주식 가치 평가 도구 (상증세법 기초)[/bold white]\n"
                "[dim]Sang-Jeung-Se Law Based Stock Valuation CLI[/dim]",
                border_style="green",
                padding=(1, 5),
            )
        )

        console.print("\n[bold cyan]실행할 모드를 선택해 주세요:[/bold cyan]")
        console.print(
            " [bold white]1.[/bold white]  [green]예시 데이터로 확인[/green] (2021~2019 기본값)"
        )
        console.print(" [bold white]2.[/bold white]  [yellow]데이터 직접 입력[/yellow]")
        console.print(" [bold white]Q.[/bold white]  [red]프로그램 종료[/red]")

        choice = Prompt.ask("\n선택", choices=["1", "2", "q", "Q"], default="1")

        if choice.lower() == "q":
            console.print("[bold red]프로그램을 종료합니다. 감사합니다.[/bold red]")
            sys.exit()

        if choice == "1":
            data = {
                "Year": [2021, 2020, 2019],
                "Shares": [394000, 394000, 394000],
                "Equity": [102396988397, 91605031590, 63655376058],
                "NetIncome": [11873196507, 6560905123, 11843188331],
            }
        else:
            latest_year = IntPrompt.ask(
                "\n[bold]평가 기준 연도 (T)[/bold]", default=2021
            )
            years = [latest_year, latest_year - 1, latest_year - 2]

            shares_list = []
            equity_list = []
            ni_list = []

            console.print(
                f"\n[dim]* {latest_year}년부터 {latest_year - 2}년까지의 데이터를 입력합니다.[/dim]"
            )
            common_shares = IntPrompt.ask(
                "3개년 발행주식수가 동일합니까? (동일하면 수량 입력, 다르면 0 입력)",
                default=394000,
            )

            for year in years:
                console.print(f"\n[bold yellow]▶ {year}년 성과 입력[/bold yellow]")
                if common_shares > 0:
                    shares = common_shares
                    console.print(f"  발행주식수: {shares:,.0f} (고정값)")
                else:
                    shares = IntPrompt.ask(f"  {year}년 발행주식수")

                equity = IntPrompt.ask(f"  {year}년 자기자본(순자산)")
                ni = IntPrompt.ask(f"  {year}년 당기순이익")

                shares_list.append(shares)
                equity_list.append(equity)
                ni_list.append(ni)

            data = {
                "Year": years,
                "Shares": shares_list,
                "Equity": equity_list,
                "NetIncome": ni_list,
            }

        with console.status("[bold green]가치 평가 계산 중..."):
            results = calculate_valuation(data)

        display_results(results)

        console.print("\n" + "=" * 50)
        Prompt.ask(
            "[bold reverse] 메인 메뉴로 돌아가려면 엔터를 누르세요 [/bold reverse]"
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]사용자에 의해 프로그램이 중단되었습니다.[/bold red]")
        sys.exit()
