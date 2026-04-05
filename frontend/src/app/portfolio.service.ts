import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PortfolioItem {
    id: number;
    Symbol: string;
    Company: string;
    Quantity: number;
    BuyPrice: number;
    BuyDate: string;
    CurrentPrice: number;
    TotalInvested: number;
    CurrentTotal: number;
    Gain: number;
}

export interface PortfolioSummary {
    total_invested: number;
    total_value: number;
    total_gain: number;
    total_realized_gain: number;
}


export interface PortfolioResponse {
    data: PortfolioItem[];
    summary: PortfolioSummary;
}

@Injectable({
    providedIn: 'root'
})
export class PortfolioService {
    private apiUrl = 'http://localhost:8000/api/portfolio'; // FastAPI backend

    constructor(private http: HttpClient) { }

    getPortfolio(): Observable<PortfolioResponse> {
        return this.http.get<PortfolioResponse>(this.apiUrl);
    }

    getRadar(): Observable<any[]> {
        return this.http.get<any[]>('http://localhost:8000/api/radar');
    }

    getNews(category: string): Observable<any[]> {
        return this.http.get<any[]>(`http://localhost:8000/api/news/${category}`);
    }

    addPortfolioItem(item: { symbol: string, quantity: number, buy_price: number }): Observable<any> {
        return this.http.post(this.apiUrl, item);
    }

    deletePortfolioItem(id: number): Observable<any> {
        return this.http.delete(`${this.apiUrl}/${id}`);
    }

    updatePortfolioItem(id: number, payload: any): Observable<any> {
        return this.http.put(`${this.apiUrl}/${id}`, payload);
    }

    sellPortfolioItem(id: number, payload: { sell_price: number, sell_date: string, quantity: number }): Observable<any> {
        return this.http.post(`${this.apiUrl}/${id}/sell`, payload);
    }

    saveHistoricalPrices(payload: { date: string, time: string, assets: { symbol: string, price: number }[] }): Observable<any> {
        const baseUrl = this.apiUrl.replace('/portfolio', '');
        return this.http.post(`${baseUrl}/historical-prices`, payload);
    }

    getHistoricalPrices(): Observable<any> {
        const baseUrl = this.apiUrl.replace('/portfolio', '');
        return this.http.get(`${baseUrl}/historical-prices`);
    }

    getQuote(symbol: string): Observable<any> {
        // En base a la URL actual 'http://localhost:8000/api/portfolio'
        // Calculamos la base para llamar a '/api/quote/:symbol'
        const baseUrl = this.apiUrl.replace('/portfolio', '');
        return this.http.get(`${baseUrl}/quote/${symbol}`);
    }
    getExchangeRate(): Observable<any> {
        const baseUrl = this.apiUrl.replace('/portfolio', '');
        return this.http.get(`${baseUrl}/exchange-rate`);
    }

    shutdownSystem(): Observable<any> {
        const baseUrl = this.apiUrl.replace('/portfolio', '');
        return this.http.post(`${baseUrl}/shutdown`, {});
    }
}
