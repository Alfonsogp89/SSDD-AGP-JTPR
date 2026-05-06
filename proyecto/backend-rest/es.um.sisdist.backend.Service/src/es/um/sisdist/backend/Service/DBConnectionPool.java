package es.um.sisdist.backend.Service;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import java.sql.Connection;
import java.sql.SQLException;

public class DBConnectionPool
{
    private static volatile HikariDataSource dataSource;

    private DBConnectionPool() {}

    public static Connection getConnection() throws SQLException
    {
        if (dataSource == null)
        {
            synchronized (DBConnectionPool.class)
            {
                if (dataSource == null)
                {
                    String url = System.getenv("DATABASE_URL");
                    if (url == null)
                        url = "jdbc:mysql://db-mysql:3306/ssdd?useSSL=false&serverTimezone=UTC";
                    String user = System.getenv("MYSQL_USER") != null ? System.getenv("MYSQL_USER") : "root";
                    String pass = System.getenv("MYSQL_PASSWORD") != null ? System.getenv("MYSQL_PASSWORD")
                                : (System.getenv("MYSQL_ROOT_PASSWORD") != null ? System.getenv("MYSQL_ROOT_PASSWORD") : "");
                    HikariConfig cfg = new HikariConfig();
                    cfg.setJdbcUrl(url);
                    cfg.setUsername(user);
                    cfg.setPassword(pass);
                    cfg.setMaximumPoolSize(10);
                    cfg.setMinimumIdle(2);
                    dataSource = new HikariDataSource(cfg);
                }
            }
        }
        return dataSource.getConnection();
    }
}
